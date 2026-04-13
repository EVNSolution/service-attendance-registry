from django.db.models import Q
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from attendanceregistry.models import AttendanceDay
from attendanceregistry.permissions import AuthenticatedReadAdminWrite
from attendanceregistry.permissions_navigation import require_nav_access
from attendanceregistry.serializers import (
    AttendanceBulkLookupRequestSerializer,
    AttendanceDaySerializer,
    DispatchSignalSyncRequestSerializer,
    MyAttendanceDaysQuerySerializer,
    MyAttendanceDaysResponseSerializer,
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


class MyAttendanceDayListView(APIView):
    permission_classes = [AuthenticatedReadAdminWrite]

    def get(self, request):
        principal = request.user
        if getattr(principal, "active_account_type", None) != "driver" or not getattr(
            principal, "driver_id", None
        ):
            raise PermissionDenied("Driver session required.")

        query_serializer = MyAttendanceDaysQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        queryset = AttendanceDay.objects.filter(driver_id=principal.driver_id)
        date_from = query_serializer.validated_data.get("date_from")
        date_to = query_serializer.validated_data.get("date_to")
        if date_from is not None:
            queryset = queryset.filter(attendance_date__gte=date_from)
        if date_to is not None:
            queryset = queryset.filter(attendance_date__lte=date_to)
        queryset = queryset.order_by("-attendance_date")

        response_serializer = MyAttendanceDaysResponseSerializer(
            {
                "driver_id": principal.driver_id,
                "days": queryset,
            }
        )
        return Response(response_serializer.data)
