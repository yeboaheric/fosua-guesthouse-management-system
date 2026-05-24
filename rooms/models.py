from django.db import models


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
    base_rate = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["room_number"]

    def __str__(self):
        return f"Room {self.room_number} ({self.get_room_type_display()})"
