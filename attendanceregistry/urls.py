from django.urls import path

from attendanceregistry.views import (
    AttendanceBulkLookupView,
    AttendanceDayDetailView,
    AttendanceDayListView,
    DispatchSignalSyncView,
    HealthView,
)

urlpatterns = [
    path("days/", AttendanceDayListView.as_view(), name="attendance-day-list"),
    path("days/<uuid:attendance_day_id>/", AttendanceDayDetailView.as_view(), name="attendance-day-detail"),
    path("internal/dispatch-signals:sync/", DispatchSignalSyncView.as_view(), name="dispatch-signal-sync"),
    path("internal/days:bulk-lookup/", AttendanceBulkLookupView.as_view(), name="attendance-day-bulk-lookup"),
    path("health/", HealthView.as_view(), name="health"),
]
