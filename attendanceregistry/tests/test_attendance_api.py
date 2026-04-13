from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient

from attendanceregistry.models import AttendanceDay


class AttendanceApiTests(TestCase):
    def setUp(self) -> None:
        self.driver_id = str(uuid4())
        self.other_driver_id = str(uuid4())
        self.attendance_date = "2026-04-12"
        self.admin_client = APIClient()
        self.admin_client.credentials(HTTP_AUTHORIZATION=f"Bearer {self._issue_token('admin')}")
        self.user_client = APIClient()
        self.user_client.credentials(HTTP_AUTHORIZATION=f"Bearer {self._issue_token('user')}")
        self.driver_client = APIClient()
        self.driver_client.credentials(
            HTTP_AUTHORIZATION=(
                f"Bearer {self._issue_token('user', active_account_type='driver', driver_id=self.driver_id)}"
            )
        )

    def _issue_token(
        self,
        role: str,
        *,
        active_account_type: str | None = None,
        driver_id: str | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(uuid4()),
            "email": f"{role}@example.com",
            "role": role,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "jti": str(uuid4()),
            "type": "access",
        }
        if active_account_type is not None:
            payload["active_account_type"] = active_account_type
        if driver_id is not None:
            payload["driver_id"] = driver_id
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def test_days_list_requires_authentication(self) -> None:
        response = APIClient().get("/days/")

        self.assertEqual(response.status_code, 401)

    def test_admin_can_sync_dispatch_signals_and_lookup_days(self) -> None:
        sync_response = self.admin_client.post(
            "/internal/dispatch-signals:sync/",
            {
                "signals": [
                    {
                        "driver_id": self.driver_id,
                        "attendance_date": self.attendance_date,
                        "source_reference": "batch-001:row-1",
                        "small_region_text": "10H2",
                        "detailed_region_text": "배송없음",
                        "box_count": 0,
                        "household_count": 0,
                        "raw_reason_code": "dispatch_upload_confirm",
                        "raw_payload": {"batch_id": "batch-001"},
                    }
                ]
            },
            format="json",
        )

        self.assertEqual(sync_response.status_code, 200)
        self.assertEqual(sync_response.data["signals_received"], 1)
        self.assertEqual(sync_response.data["days"][0]["final_status"], "day_off")

        lookup_response = self.admin_client.post(
            "/internal/days:bulk-lookup/",
            {
                "keys": [
                    {
                        "driver_id": self.driver_id,
                        "attendance_date": self.attendance_date,
                    }
                ]
            },
            format="json",
        )

        self.assertEqual(lookup_response.status_code, 200)
        self.assertEqual(lookup_response.data["days"][0]["driver_id"], self.driver_id)
        self.assertEqual(lookup_response.data["days"][0]["final_status"], "day_off")

    def test_user_cannot_sync_dispatch_signals(self) -> None:
        response = self.user_client.post(
            "/internal/dispatch-signals:sync/",
            {"signals": []},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_me_days_rejects_non_driver_sessions(self) -> None:
        response = self.user_client.get("/me/days/", {"date_from": "2026-04-10", "date_to": "2026-04-12"})

        self.assertEqual(response.status_code, 403)

    def test_me_days_returns_only_session_driver_days_in_range(self) -> None:
        AttendanceDay.objects.create(
            driver_id=self.driver_id,
            attendance_date="2026-04-10",
            final_status="worked",
            decided_source_kind="dispatch",
        )
        AttendanceDay.objects.create(
            driver_id=self.driver_id,
            attendance_date="2026-04-11",
            final_status="day_off",
            decided_source_kind="dispatch",
        )
        AttendanceDay.objects.create(
            driver_id=self.driver_id,
            attendance_date="2026-04-13",
            final_status="worked",
            decided_source_kind="dispatch",
        )
        AttendanceDay.objects.create(
            driver_id=self.other_driver_id,
            attendance_date="2026-04-11",
            final_status="exception",
            decided_source_kind="dispatch",
        )

        response = self.driver_client.get(
            "/me/days/",
            {"date_from": "2026-04-10", "date_to": "2026-04-12"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["driver_id"], self.driver_id)
        self.assertEqual(
            [item["attendance_date"] for item in response.data["days"]],
            ["2026-04-11", "2026-04-10"],
        )
        self.assertEqual(
            [item["final_status"] for item in response.data["days"]],
            ["day_off", "worked"],
        )
