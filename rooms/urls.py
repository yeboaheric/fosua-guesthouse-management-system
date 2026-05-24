from django.urls import path

from rooms.views import room_availability, room_create, room_list, room_update

urlpatterns = [
    path("", room_list, name="room-list"),
    path("new/", room_create, name="room-create"),
    path("<int:pk>/edit/", room_update, name="room-update"),
    path("availability/", room_availability, name="room-availability"),
]
