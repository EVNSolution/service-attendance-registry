from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient


class AttendanceApiTests(TestCase):
    def setUp(self) -> None:
        self.driver_id = str(uuid4())
        self.attendance_date = "2026-04-12"
        self.admin_client = APIClient()
        self.admin_client.credentials(HTTP_AUTHORIZATION=f"Bearer {self._issue_token('admin')}")
        self.user_client = APIClient()
        self.user_client.credentials(HTTP_AUTHORIZATION=f"Bearer {self._issue_token('user')}")

    def _issue_token(self, role: str) -> str:
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
