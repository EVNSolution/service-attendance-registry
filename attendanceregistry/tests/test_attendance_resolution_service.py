from uuid import uuid4

from django.test import TestCase

from attendanceregistry.models import AttendanceDay, AttendanceSignal
from attendanceregistry.services.attendance_resolution_service import AttendanceResolutionService


class AttendanceResolutionServiceTests(TestCase):
    def setUp(self) -> None:
        self.service = AttendanceResolutionService()
        self.driver_id = str(uuid4())
        self.attendance_date = "2026-04-12"

    def _signal(self, **overrides):
        payload = {
            "driver_id": self.driver_id,
            "attendance_date": self.attendance_date,
            "source_reference": f"batch-001:{uuid4()}",
            "small_region_text": "10H2",
            "detailed_region_text": "10H2-가",
            "box_count": 12,
            "household_count": 5,
            "raw_reason_code": "dispatch_upload_confirm",
            "raw_payload": {"batch_id": "batch-001"},
        }
        payload.update(overrides)
        return payload

    def test_sync_dispatch_signal_marks_zero_box_and_household_row_as_day_off(self) -> None:
        days = self.service.sync_dispatch_signals(
            [
                self._signal(
                    detailed_region_text="배송없음",
                    box_count=0,
                    household_count=0,
                )
            ]
        )

        self.assertEqual(len(days), 1)
        self.assertEqual(days[0].final_status, AttendanceDay.FinalStatus.DAY_OFF)
        self.assertEqual(AttendanceSignal.objects.count(), 1)

    def test_sync_dispatch_signal_marks_positive_household_row_as_worked(self) -> None:
        days = self.service.sync_dispatch_signals(
            [
                self._signal(
                    box_count=0,
                    household_count=1,
                )
            ]
        )

        self.assertEqual(days[0].final_status, AttendanceDay.FinalStatus.WORKED)

    def test_sync_dispatch_signals_roll_up_multiple_rows_for_same_driver_day(self) -> None:
        days = self.service.sync_dispatch_signals(
            [
                self._signal(source_reference="batch-001:row-1", box_count=4),
                self._signal(
                    source_reference="batch-001:row-2",
                    box_count=0,
                    household_count=0,
                ),
            ]
        )

        self.assertEqual(days[0].final_status, AttendanceDay.FinalStatus.WORKED)
        self.assertEqual(AttendanceDay.objects.count(), 1)
        self.assertEqual(AttendanceSignal.objects.count(), 2)

    def test_sync_dispatch_signals_is_idempotent_per_source_reference(self) -> None:
        payload = self._signal(source_reference="batch-001:row-1", box_count=3)

        self.service.sync_dispatch_signals([payload])
        days = self.service.sync_dispatch_signals([payload])

        self.assertEqual(len(days), 1)
        self.assertEqual(AttendanceDay.objects.count(), 1)
        self.assertEqual(AttendanceSignal.objects.count(), 1)
