from datetime import datetime, time, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce

from accounts.models import StatusTrackingMixin
from guests.models import Guest
from rooms.models import Room


class Booking(StatusTrackingMixin, models.Model):
    class BookingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        CHECKED_IN = "checked_in", "Checked In"
        CHECKED_OUT = "checked_out", "Checked Out"
        CANCELLED = "cancelled", "Cancelled"

    guest = models.ForeignKey(Guest, on_delete=models.PROTECT, related_name="bookings")
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="bookings")
    check_in = models.DateField()
    check_in_time = models.TimeField(default=time(14, 0))
    check_out = models.DateField()
    check_out_time = models.TimeField(default=time(11, 0))
    adults = models.PositiveSmallIntegerField(default=1)
    children = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["check_in", "check_out"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return (
            f"{self.guest} - Room {self.room.room_number} "
            f"({self.check_in.strftime('%d/%m/%Y')} {self.check_in_time.strftime('%H:%M')} to {self.check_out.strftime('%d/%m/%Y')} {self.check_out_time.strftime('%H:%M')})"
        )

    @property
    def check_in_at(self):
        return datetime.combine(self.check_in, self.check_in_time)

    @property
    def check_out_at(self):
        return datetime.combine(self.check_out, self.check_out_time)

    @property
    def nights(self):
        return max((self.check_out - self.check_in).days, 1)

    def clean(self):
        if self.check_out_at <= self.check_in_at:
            raise ValidationError("Check-out must be after check-in time.")

        if not self.room_id:
            return

        active_statuses = [
            self.BookingStatus.PENDING,
            self.BookingStatus.CONFIRMED,
            self.BookingStatus.CHECKED_IN,
        ]
        overlapping_bookings = (
            Booking.objects.filter(room=self.room, status__in=active_statuses)
            .exclude(pk=self.pk)
            .filter(check_in__lte=self.check_out, check_out__gte=self.check_in)
        )
        for existing_booking in overlapping_bookings:
            if booking_ranges_overlap(
                self.check_in,
                self.check_in_time,
                self.check_out,
                self.check_out_time,
                existing_booking.check_in,
                existing_booking.check_in_time,
                existing_booking.check_out,
                existing_booking.check_out_time,
            ):
                raise ValidationError("This room is already booked for the selected dates.")

    def save(self, *args, **kwargs):
        if self.room_id and self.check_in and self.check_out:
            self.total_amount = self.room.base_rate * self.nights
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def amount_paid(self):
        return self.payments.aggregate(
            total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
        )["total"]

    @property
    def balance_due(self):
        return max(self.total_amount - self.amount_paid, 0)


def booking_ranges_overlap(
    first_check_in,
    first_check_in_time,
    first_check_out,
    first_check_out_time,
    second_check_in,
    second_check_in_time,
    second_check_out,
    second_check_out_time,
):
    first_start = datetime.combine(first_check_in, first_check_in_time)
    first_end = datetime.combine(first_check_out, first_check_out_time)
    second_start = datetime.combine(second_check_in, second_check_in_time)
    second_end = datetime.combine(second_check_out, second_check_out_time)
    return first_start < second_end and first_end > second_start


def booking_occupied_end_date(check_in, check_out):
    return check_out if check_in == check_out else check_out - timedelta(days=1)


def booking_occupies_day(check_in, check_out, current_day):
    return check_in <= current_day <= booking_occupied_end_date(check_in, check_out)


def booking_occupied_days_in_range(check_in, check_out, start_date, end_date):
    overlap_start = max(check_in, start_date)
    overlap_end = min(booking_occupied_end_date(check_in, check_out), end_date)
    if overlap_end < overlap_start:
        return 0
    return (overlap_end - overlap_start).days + 1


class Payment(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        MOBILE_MONEY = "mobile_money", "Mobile Money"
        CARD = "card", "Card"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
    )
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments_received",
    )
    paid_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-paid_at"]

    def __str__(self):
        return f"Payment {self.amount} for booking #{self.booking_id}"


class EventBooking(StatusTrackingMixin, models.Model):
    class EventBookingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class SetupStyle(models.TextChoices):
        THEATER = "theater", "Theater"
        CLASSROOM = "classroom", "Classroom"
        BANQUET = "banquet", "Banquet"
        BOARDROOM = "boardroom", "Boardroom"
        OTHER = "other", "Other"

    guest = models.ForeignKey(
        Guest,
        on_delete=models.PROTECT,
        related_name="event_bookings",
    )
    event_space_name = models.CharField(max_length=120, default="Main Event Space")
    event_title = models.CharField(max_length=150)
    purpose = models.TextField()
    expected_guests = models.PositiveIntegerField()
    event_start = models.DateTimeField()
    event_end = models.DateTimeField()
    setup_style = models.CharField(
        max_length=20,
        choices=SetupStyle.choices,
        default=SetupStyle.BANQUET,
    )
    needs_catering = models.BooleanField(default=False)
    needs_audio_visual = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=EventBookingStatus.choices,
        default=EventBookingStatus.PENDING,
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="event_bookings_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_start", "event_end"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.event_title} ({self.event_space_name})"

    def clean(self):
        if self.event_end <= self.event_start:
            raise ValidationError("Event end time must be after start time.")

        active_statuses = [
            self.EventBookingStatus.PENDING,
            self.EventBookingStatus.CONFIRMED,
            self.EventBookingStatus.IN_PROGRESS,
        ]
        overlapping_bookings = (
            EventBooking.objects.filter(
                event_space_name=self.event_space_name,
                status__in=active_statuses,
            )
            .exclude(pk=self.pk)
            .filter(event_start__lt=self.event_end, event_end__gt=self.event_start)
        )
        if overlapping_bookings.exists():
            raise ValidationError("This event space is already reserved for that time range.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def amount_paid(self):
        return self.payments.aggregate(
            total=Coalesce(
                Sum("amount"),
                Value(0, output_field=DecimalField(max_digits=10, decimal_places=2)),
            )
        )["total"]

    @property
    def balance_due(self):
        return max(self.total_amount - self.amount_paid, 0)


class EventPayment(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        MOBILE_MONEY = "mobile_money", "Mobile Money"
        CARD = "card", "Card"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"

    event_booking = models.ForeignKey(
        EventBooking,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
    )
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="event_payments_received",
    )
    paid_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-paid_at"]

    def __str__(self):
        return f"Payment {self.amount} for event booking #{self.event_booking_id}"
