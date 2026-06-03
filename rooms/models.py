from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
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
        if self.pk:
            previous = Room.objects.filter(pk=self.pk).values(
                "status",
                "status_started_at",
                "last_status_changed_at",
            ).first()
            if previous:
                if previous["status"] != self.status:
                    self.status_started_at = now
                elif not self.status_started_at:
                    self.status_started_at = previous["status_started_at"] or now

                self.last_status_changed_at = now
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
