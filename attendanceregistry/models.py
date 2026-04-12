import uuid

from django.db import models


class AttendanceSignal(models.Model):
    class SourceKind(models.TextChoices):
        DISPATCH = "dispatch", "dispatch"

    class SuggestedStatus(models.TextChoices):
        WORKED = "worked", "worked"
        DAY_OFF = "day_off", "day_off"
        EXCEPTION = "exception", "exception"

    attendance_signal_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver_id = models.UUIDField()
    attendance_date = models.DateField()
    source_kind = models.CharField(
        max_length=32,
        choices=SourceKind.choices,
        default=SourceKind.DISPATCH,
    )
    suggested_status = models.CharField(max_length=32, choices=SuggestedStatus.choices)
    raw_reason_code = models.CharField(max_length=64, blank=True, default="")
    raw_payload = models.JSONField(default=dict, blank=True)
    source_reference = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("attendance_date", "driver_id", "source_reference")
        constraints = [
            models.UniqueConstraint(
                fields=("source_kind", "source_reference"),
                name="unique_attendance_signal_per_source_reference",
            )
        ]


class AttendanceDay(models.Model):
    class FinalStatus(models.TextChoices):
        WORKED = "worked", "worked"
        DAY_OFF = "day_off", "day_off"
        EXCEPTION = "exception", "exception"

    attendance_day_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver_id = models.UUIDField()
    attendance_date = models.DateField()
    final_status = models.CharField(max_length=32, choices=FinalStatus.choices)
    decided_source_kind = models.CharField(max_length=32, default=AttendanceSignal.SourceKind.DISPATCH)
    decided_signal = models.ForeignKey(
        AttendanceSignal,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="decided_days",
        db_column="decided_signal_id",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("attendance_date", "driver_id")
        constraints = [
            models.UniqueConstraint(
                fields=("driver_id", "attendance_date"),
                name="unique_attendance_day_per_driver_date",
            )
        ]
