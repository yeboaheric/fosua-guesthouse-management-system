from django.urls import path

from rooms.views import (
    room_availability,
    room_create,
    room_list,
    room_update,
    housekeeping_dashboard,
    housekeeping_update_status,
    housekeeping_task_list,
    housekeeping_task_create,
    housekeeping_task_update,
    housekeeping_task_complete,
    housekeeping_history,
)

urlpatterns = [
    path("", room_list, name="room-list"),
    path("new/", room_create, name="room-create"),
    path("<int:pk>/edit/", room_update, name="room-update"),
    path("availability/", room_availability, name="room-availability"),
    path("housekeeping/", housekeeping_dashboard, name="housekeeping-dashboard"),
    path("housekeeping/status/", housekeeping_update_status, name="housekeeping-update-status"),
    path("housekeeping/status/<int:pk>/", housekeeping_update_status, name="housekeeping-update-status-room"),
    path("housekeeping/tasks/", housekeeping_task_list, name="housekeeping-tasks"),
    path("housekeeping/tasks/new/", housekeeping_task_create, name="housekeeping-task-create"),
    path("housekeeping/tasks/<int:pk>/edit/", housekeeping_task_update, name="housekeeping-task-update"),
    path("housekeeping/tasks/<int:pk>/complete/", housekeeping_task_complete, name="housekeeping-task-complete"),
    path("housekeeping/history/", housekeeping_history, name="housekeeping-history"),
]
