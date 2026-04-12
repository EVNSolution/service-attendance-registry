from rest_framework import serializers

from attendanceregistry.models import AttendanceDay

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class AttendanceDaySerializer(serializers.ModelSerializer):
    decided_signal_id = serializers.UUIDField(source="decided_signal.attendance_signal_id", read_only=True)
    created_at = serializers.DateTimeField(format=DATETIME_FORMAT, read_only=True)
    updated_at = serializers.DateTimeField(format=DATETIME_FORMAT, read_only=True)

    class Meta:
        model = AttendanceDay
        fields = (
            "attendance_day_id",
            "driver_id",
            "attendance_date",
            "final_status",
            "decided_source_kind",
            "decided_signal_id",
            "created_at",
            "updated_at",
        )


class DispatchSignalSyncItemSerializer(serializers.Serializer):
    driver_id = serializers.UUIDField()
    attendance_date = serializers.DateField()
    source_reference = serializers.CharField(max_length=255)
    small_region_text = serializers.CharField(required=False, allow_blank=True, default="")
    detailed_region_text = serializers.CharField(required=False, allow_blank=True, default="")
    box_count = serializers.IntegerField(min_value=0)
    household_count = serializers.IntegerField(min_value=0)
    raw_reason_code = serializers.CharField(required=False, allow_blank=True, default="")
    raw_payload = serializers.JSONField(required=False, default=dict)


class DispatchSignalSyncRequestSerializer(serializers.Serializer):
    signals = DispatchSignalSyncItemSerializer(many=True)


class AttendanceBulkLookupKeySerializer(serializers.Serializer):
    driver_id = serializers.UUIDField()
    attendance_date = serializers.DateField()


class AttendanceBulkLookupRequestSerializer(serializers.Serializer):
    keys = AttendanceBulkLookupKeySerializer(many=True)
