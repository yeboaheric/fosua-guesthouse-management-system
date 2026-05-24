from django.urls import path

from bookings.views import (
    booking_cancel,
    booking_check_in,
    booking_check_out,
    booking_confirm,
    booking_create,
    booking_list,
    booking_payments,
    booking_update,
    operations_overview,
)

urlpatterns = [
    path("", booking_list, name="booking-list"),
    path("new/", booking_create, name="booking-create"),
    path("<int:pk>/edit/", booking_update, name="booking-update"),
    path("<int:pk>/confirm/", booking_confirm, name="booking-confirm"),
    path("<int:pk>/check-in/", booking_check_in, name="booking-check-in"),
    path("<int:pk>/check-out/", booking_check_out, name="booking-check-out"),
    path("<int:pk>/cancel/", booking_cancel, name="booking-cancel"),
    path("<int:pk>/payments/", booking_payments, name="booking-payments"),
    path("operations/", operations_overview, name="operations-overview"),
]
