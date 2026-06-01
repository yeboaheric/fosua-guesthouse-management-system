from django.db import models
from django.utils import timezone


class Room(models.Model):
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
            previous = Room.objects.filter(pk=self.pk).values("status", "status_started_at").first()
            if previous and previous["status"] != self.status:
                self.status_started_at = now
                self.last_status_changed_at = now
            elif previous and previous["status_started_at"] and not self.status_started_at:
                self.status_started_at = previous["status_started_at"]
        else:
            self.status_started_at = self.status_started_at or now
            self.last_status_changed_at = self.last_status_changed_at or now

        if not self.last_status_changed_at:
            self.last_status_changed_at = now
        if not self.status_started_at:
            self.status_started_at = now

        return super().save(*args, **kwargs)
