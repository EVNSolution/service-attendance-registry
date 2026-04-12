from django.db.models import Q
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from attendanceregistry.models import AttendanceDay
from attendanceregistry.permissions import AuthenticatedReadAdminWrite
from attendanceregistry.permissions_navigation import require_nav_access
from attendanceregistry.serializers import (
    AttendanceBulkLookupRequestSerializer,
    AttendanceDaySerializer,
    DispatchSignalSyncRequestSerializer,
)
from attendanceregistry.services.attendance_resolution_service import AttendanceResolutionService


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"status": "ok"})


class AttendanceDayListView(generics.ListAPIView):
    permission_classes = [AuthenticatedReadAdminWrite]
    serializer_class = AttendanceDaySerializer

    def get_queryset(self):
        require_nav_access(self.request, "dispatch", "settlements")
        queryset = AttendanceDay.objects.all().order_by("attendance_date", "driver_id")
        driver_id = self.request.query_params.get("driver_id")
        attendance_date = self.request.query_params.get("attendance_date")
        final_status = self.request.query_params.get("final_status")
        if driver_id:
            queryset = queryset.filter(driver_id=driver_id)
        if attendance_date:
            queryset = queryset.filter(attendance_date=attendance_date)
        if final_status:
            queryset = queryset.filter(final_status=final_status)
        return queryset


class AttendanceDayDetailView(generics.RetrieveAPIView):
    permission_classes = [AuthenticatedReadAdminWrite]
    serializer_class = AttendanceDaySerializer
    queryset = AttendanceDay.objects.all()
    lookup_field = "attendance_day_id"

    def get_object(self):
        require_nav_access(self.request, "dispatch", "settlements")
        return super().get_object()


class DispatchSignalSyncView(APIView):
    permission_classes = [AuthenticatedReadAdminWrite]

    def post(self, request):
        require_nav_access(request, "dispatch")
        serializer = DispatchSignalSyncRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        days = AttendanceResolutionService().sync_dispatch_signals(serializer.validated_data["signals"])
        return Response(
            {
                "signals_received": len(serializer.validated_data["signals"]),
                "days": AttendanceDaySerializer(days, many=True).data,
            }
        )


class AttendanceBulkLookupView(APIView):
    permission_classes = [AuthenticatedReadAdminWrite]

    def post(self, request):
        require_nav_access(request, "dispatch", "settlements")
        serializer = AttendanceBulkLookupRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query = Q()
        for key in serializer.validated_data["keys"]:
            query |= Q(driver_id=key["driver_id"], attendance_date=key["attendance_date"])

        if not query:
            return Response({"days": []})

        days = AttendanceDay.objects.filter(query).order_by("attendance_date", "driver_id")
        return Response({"days": AttendanceDaySerializer(days, many=True).data})
