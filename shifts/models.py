from django.conf import settings
from django.db import models


class ShiftHandover(models.Model):
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField()
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="shift_handovers_prepared",
    )
    summary = models.TextField(blank=True)

    check_ins_count = models.PositiveIntegerField(default=0)
    check_outs_count = models.PositiveIntegerField(default=0)
    reservations_count = models.PositiveIntegerField(default=0)
    cancellations_count = models.PositiveIntegerField(default=0)
    maintenance_rooms_count = models.PositiveIntegerField(default=0)
    cleaning_rooms_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-ended_at", "-created_at"]

    def __str__(self):
        return f"Handover #{self.id} ({self.started_at:%Y-%m-%d %H:%M} - {self.ended_at:%H:%M})"


class ShiftHandoverUpdate(models.Model):
    handover = models.ForeignKey(
        ShiftHandover,
        on_delete=models.CASCADE,
        related_name="updates",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="shift_handover_updates",
    )
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Update #{self.id} on handover #{self.handover_id}"
