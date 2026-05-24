from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce

from guests.models import Guest
from rooms.models import Room


class Booking(models.Model):
    class BookingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        CHECKED_IN = "checked_in", "Checked In"
        CHECKED_OUT = "checked_out", "Checked Out"
        CANCELLED = "cancelled", "Cancelled"

    guest = models.ForeignKey(Guest, on_delete=models.PROTECT, related_name="bookings")
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="bookings")
    check_in = models.DateField()
    check_out = models.DateField()
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
        return f"{self.guest} - Room {self.room.room_number} ({self.check_in} to {self.check_out})"

    def clean(self):
        if self.check_out <= self.check_in:
            raise ValidationError("Check-out date must be after check-in date.")

        active_statuses = [
            self.BookingStatus.PENDING,
            self.BookingStatus.CONFIRMED,
            self.BookingStatus.CHECKED_IN,
        ]
        overlapping_bookings = (
            Booking.objects.filter(room=self.room, status__in=active_statuses)
            .exclude(pk=self.pk)
            .filter(check_in__lt=self.check_out, check_out__gt=self.check_in)
        )
        if overlapping_bookings.exists():
            raise ValidationError("This room is already booked for the selected dates.")

    def save(self, *args, **kwargs):
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
