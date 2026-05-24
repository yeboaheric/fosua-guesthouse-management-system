from django.urls import path

from guests.views import guest_create, guest_list, guest_update

urlpatterns = [
    path("", guest_list, name="guest-list"),
    path("new/", guest_create, name="guest-create"),
    path("<int:pk>/edit/", guest_update, name="guest-update"),
]
