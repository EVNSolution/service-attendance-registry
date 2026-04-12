from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from attendanceregistry.models import AttendanceDay, AttendanceSignal


@dataclass(frozen=True)
class DriverDayKey:
    driver_id: str
    attendance_date: str


class AttendanceResolutionService:
    def sync_dispatch_signals(self, signals: list[dict]) -> list[AttendanceDay]:
        updated_keys: set[DriverDayKey] = set()

        with transaction.atomic():
            for payload in signals:
                signal = self._upsert_dispatch_signal(payload)
                updated_keys.add(
                    DriverDayKey(
                        driver_id=str(signal.driver_id),
                        attendance_date=str(signal.attendance_date),
                    )
                )

            days = [
                self._rebuild_day(
                    driver_id=driver_day_key.driver_id,
                    attendance_date=driver_day_key.attendance_date,
                )
                for driver_day_key in sorted(updated_keys, key=lambda item: (item.attendance_date, item.driver_id))
            ]

        return days

    def _upsert_dispatch_signal(self, payload: dict) -> AttendanceSignal:
        defaults = {
            "driver_id": payload["driver_id"],
            "attendance_date": payload["attendance_date"],
            "suggested_status": self._resolve_dispatch_status(payload),
            "raw_reason_code": payload.get("raw_reason_code", ""),
            "raw_payload": {
                **payload.get("raw_payload", {}),
                "small_region_text": payload.get("small_region_text", ""),
                "detailed_region_text": payload.get("detailed_region_text", ""),
                "box_count": payload.get("box_count", 0),
            },
        }
        signal, _ = AttendanceSignal.objects.update_or_create(
            source_kind=AttendanceSignal.SourceKind.DISPATCH,
            source_reference=payload["source_reference"],
            defaults=defaults,
        )
        return signal

    def _rebuild_day(self, *, driver_id: str, attendance_date: str) -> AttendanceDay:
        signals = list(
            AttendanceSignal.objects.filter(
                driver_id=driver_id,
                attendance_date=attendance_date,
                source_kind=AttendanceSignal.SourceKind.DISPATCH,
            ).order_by("created_at", "source_reference")
        )

        final_status = self._resolve_final_status(signals)
        deciding_signal = self._select_deciding_signal(signals, final_status)
        day, _ = AttendanceDay.objects.update_or_create(
            driver_id=driver_id,
            attendance_date=attendance_date,
            defaults={
                "final_status": final_status,
                "decided_source_kind": AttendanceSignal.SourceKind.DISPATCH,
                "decided_signal": deciding_signal,
            },
        )
        return day

    def _resolve_dispatch_status(self, payload: dict) -> str:
        small_region_text = str(payload.get("small_region_text", "")).strip()
        box_count = int(payload.get("box_count", 0) or 0)

        if small_region_text == "00":
            if box_count > 0:
                return AttendanceSignal.SuggestedStatus.EXCEPTION
            return AttendanceSignal.SuggestedStatus.DAY_OFF
        return AttendanceSignal.SuggestedStatus.WORKED

    def _resolve_final_status(self, signals: list[AttendanceSignal]) -> str:
        statuses = {signal.suggested_status for signal in signals}
        if AttendanceSignal.SuggestedStatus.EXCEPTION in statuses:
            return AttendanceDay.FinalStatus.EXCEPTION
        if statuses == {AttendanceSignal.SuggestedStatus.DAY_OFF}:
            return AttendanceDay.FinalStatus.DAY_OFF
        return AttendanceDay.FinalStatus.WORKED

    def _select_deciding_signal(
        self,
        signals: list[AttendanceSignal],
        final_status: str,
    ) -> AttendanceSignal | None:
        if not signals:
            return None

        priority = {
            AttendanceDay.FinalStatus.EXCEPTION: AttendanceSignal.SuggestedStatus.EXCEPTION,
            AttendanceDay.FinalStatus.DAY_OFF: AttendanceSignal.SuggestedStatus.DAY_OFF,
            AttendanceDay.FinalStatus.WORKED: AttendanceSignal.SuggestedStatus.WORKED,
        }
        target = priority[final_status]
        for signal in signals:
            if signal.suggested_status == target:
                return signal
        return signals[0]
