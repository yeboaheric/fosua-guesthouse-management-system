from django.urls import path

from rooms.views import (
    housekeeping_dashboard,
    housekeeping_log_delete,
    housekeeping_log_edit,
    housekeeping_report_export,
    room_availability,
    room_create,
    room_list,
    room_update,
)

urlpatterns = [
    path("", room_list, name="room-list"),
    path("new/", room_create, name="room-create"),
    path("<int:pk>/edit/", room_update, name="room-update"),
    path("availability/", room_availability, name="room-availability"),
    path("housekeeping/", housekeeping_dashboard, name="housekeeping-dashboard"),
    path("housekeeping/logs/<int:pk>/edit/", housekeeping_log_edit, name="housekeeping-log-edit"),
    path("housekeeping/logs/<int:pk>/delete/", housekeeping_log_delete, name="housekeeping-log-delete"),
    path("housekeeping/reports/<slug:report_range>/export/", housekeeping_report_export, name="housekeeping-report-export"),
]
