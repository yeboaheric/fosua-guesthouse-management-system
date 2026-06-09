from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from accounts.models import StatusTrackingMixin


class Room(StatusTrackingMixin, models.Model):
    class RoomType(models.TextChoices):
        STANDARD = "standard", "Standard"
        DELUXE = "deluxe", "Deluxe"

    class RoomStatus(models.TextChoices):
        AVAILABLE = "available", "Available"
        OCCUPIED = "occupied", "Occupied"
        MAINTENANCE = "maintenance", "Maintenance"
        CLEANING = "cleaning", "Cleaning In Progress"

    room_number = models.CharField(max_length=10, unique=True)
    room_type = models.CharField(max_length=20, choices=RoomType.choices)
    status = models.CharField(
        max_length=20,
        choices=RoomStatus.choices,
        default=RoomStatus.AVAILABLE,
    )
    status_started_at = models.DateTimeField(blank=True, null=True)
    last_status_changed_at = models.DateTimeField(blank=True, null=True)
    base_rate = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["room_number"]

    def __str__(self):
        return f"Room {self.room_number} ({self.get_room_type_display()})"

    def save(self, *args, **kwargs):
        now = timezone.now()
        update_fields = kwargs.get("update_fields")
        if self.pk:
            previous = Room.objects.filter(pk=self.pk).values(
                "status",
                "status_started_at",
                "last_status_changed_at",
            ).first()
            if previous:
                previous_started_at = previous["status_started_at"] or now
                previous_changed_at = previous["last_status_changed_at"] or previous_started_at
                if self.status != previous["status"]:
                    self.status_started_at = now
                    self.last_status_changed_at = now
                    if update_fields is not None:
                        kwargs["update_fields"] = set(update_fields) | {
                            "status_started_at",
                            "last_status_changed_at",
                        }
                else:
                    self.status_started_at = previous_started_at
                    self.last_status_changed_at = previous_changed_at
        else:
            self.status_started_at = self.status_started_at or now
            self.last_status_changed_at = self.last_status_changed_at or now

        if not self.status_started_at:
            self.status_started_at = now
        if not self.last_status_changed_at:
            self.last_status_changed_at = now

        return super().save(*args, **kwargs)


class MaintenanceRequest(StatusTrackingMixin, models.Model):
    class RequestStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="maintenance_requests")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenance_requests",
    )
    description = models.TextField()
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenance_assignments",
    )
    status = models.CharField(
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Maintenance for Room {self.room.room_number} ({self.get_status_display()})"


class HousekeepingItem(models.Model):
    name = models.CharField(max_length=160, unique=True)
    initial_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(0.001)],
    )
    quantity_in_stock = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
    )
    low_stock_threshold = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        help_text="Optional custom alert threshold for this item.",
    )
    unit = models.CharField(max_length=40)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="housekeeping_items",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.quantity_in_stock is None:
            self.quantity_in_stock = self.initial_quantity
        if self.quantity_in_stock is not None and self.initial_quantity is not None:
            if self.quantity_in_stock > self.initial_quantity:
                raise ValidationError(
                    {"quantity_in_stock": "Quantity in stock cannot be greater than initial quantity."}
                )

    def save(self, *args, **kwargs):
        if self._state.adding and self.quantity_in_stock in (None, Decimal("0"), 0):
            self.quantity_in_stock = self.initial_quantity
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def effective_low_stock_threshold(self):
        if self.low_stock_threshold is not None:
            return self.low_stock_threshold
        return Decimal(self.initial_quantity or 0) * Decimal("0.20")

    @property
    def is_low_stock(self):
        return Decimal(self.quantity_in_stock or 0) <= Decimal(self.effective_low_stock_threshold or 0)


class HousekeepingItemLog(models.Model):
    item = models.ForeignKey(
        HousekeepingItem,
        on_delete=models.PROTECT,
        related_name="usage_logs",
    )
    item_name = models.CharField(max_length=160)
    initial_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(0.001)],
    )
    quantity_used = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(0.001)],
    )
    quantity_in_stock = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
    )
    low_stock_threshold = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        help_text="Optional custom alert threshold for this item.",
    )
    unit = models.CharField(max_length=40)
    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        related_name="item_usage_logs",
        blank=True,
        null=True,
    )
    used_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="housekeeping_item_logs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "housekeeping_items_log"
        ordering = ["-used_at", "-created_at"]
        indexes = [
            models.Index(fields=["used_at"]),
            models.Index(fields=["item_name"]),
        ]

    def __str__(self):
        room_label = self.room.room_number if self.room_id else "General"
        return f"{self.item_name} ({self.quantity_used} {self.unit}) for {room_label}"

    def clean(self):
        super().clean()
        if not self.item_id:
            raise ValidationError({"item": "Select an item."})

        self.item_name = self.item.name
        self.initial_quantity = self.item.initial_quantity
        self.unit = self.item.unit
        self.low_stock_threshold = self.item.low_stock_threshold

        available_stock = Decimal(self.item.quantity_in_stock or 0)
        if self.pk:
            previous = HousekeepingItemLog.objects.filter(pk=self.pk).values("item_id", "quantity_used").first()
            if previous and previous["item_id"] == self.item_id:
                available_stock += Decimal(previous["quantity_used"] or 0)

        if self.quantity_used is not None:
            if self.quantity_used > available_stock:
                raise ValidationError(
                    {"quantity_used": "Quantity used cannot be greater than the available quantity in stock."}
                )
            preview_stock = available_stock - Decimal(self.quantity_used)
            self.quantity_in_stock = preview_stock if preview_stock >= 0 else Decimal("0")

    def save(self, *args, **kwargs):
        previous_item_id = None
        if self.pk:
            previous_item_id = HousekeepingItemLog.objects.filter(pk=self.pk).values_list("item_id", flat=True).first()

        self.full_clean()
        with transaction.atomic():
            result = super().save(*args, **kwargs)
            affected_item_ids = {self.item_id}
            if previous_item_id:
                affected_item_ids.add(previous_item_id)
            for item_id in affected_item_ids:
                _sync_housekeeping_item_state(item_id)
        return result

    def delete(self, *args, **kwargs):
        item_id = self.item_id
        with transaction.atomic():
            result = super().delete(*args, **kwargs)
            if item_id:
                _sync_housekeeping_item_state(item_id)
        return result

    @property
    def effective_low_stock_threshold(self):
        if self.low_stock_threshold is not None:
            return self.low_stock_threshold
        return Decimal(self.initial_quantity or 0) * Decimal("0.20")

    @property
    def is_low_stock(self):
        return Decimal(self.quantity_in_stock or 0) <= Decimal(self.effective_low_stock_threshold or 0)


def _sync_housekeeping_item_state(item_id):
    if not item_id:
        return

    item = HousekeepingItem.objects.filter(pk=item_id).first()
    if item is None:
        return

    remaining_stock = Decimal(item.initial_quantity or 0)
    logs = list(item.usage_logs.order_by("used_at", "created_at", "pk"))

    for log in logs:
        remaining_stock -= Decimal(log.quantity_used or 0)
        if remaining_stock < 0:
            remaining_stock = Decimal("0")
        log.item_name = item.name
        log.initial_quantity = item.initial_quantity
        log.quantity_in_stock = remaining_stock
        log.low_stock_threshold = item.low_stock_threshold
        log.unit = item.unit

    if logs:
        HousekeepingItemLog.objects.bulk_update(
            logs,
            ["item_name", "initial_quantity", "quantity_in_stock", "low_stock_threshold", "unit"],
        )

    HousekeepingItem.objects.filter(pk=item.pk).update(
        quantity_in_stock=remaining_stock,
        updated_at=timezone.now(),
    )
