from django.contrib import admin

from bookings.models import Booking, EventBooking, EventPayment, Payment


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "guest",
        "room",
        "check_in",
        "check_out",
        "status",
        "total_amount",
        "updated_at",
    )
    list_filter = ("status", "check_in", "check_out")
    search_fields = (
        "guest__first_name",
        "guest__last_name",
        "room__room_number",
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("booking", "amount", "method", "reference", "received_by", "paid_at")
    list_filter = ("method", "paid_at")
    search_fields = ("booking__guest__first_name", "booking__guest__last_name", "reference")


@admin.register(EventBooking)
class EventBookingAdmin(admin.ModelAdmin):
    list_display = (
        "event_title",
        "event_space_name",
        "guest",
        "event_start",
        "event_end",
        "expected_guests",
        "status",
    )
    list_filter = ("status", "event_space_name", "event_start")
    search_fields = (
        "event_title",
        "event_space_name",
        "guest__first_name",
        "guest__last_name",
    )


@admin.register(EventPayment)
class EventPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "event_booking",
        "amount",
        "method",
        "reference",
        "received_by",
        "paid_at",
    )
    list_filter = ("method", "paid_at")
    search_fields = ("event_booking__event_title", "event_booking__guest__last_name", "reference")
