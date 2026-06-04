from django.conf import settings
from django.db import models
from django.utils import timezone


class Shift(models.Model):
    """Represents a work shift (e.g., Morning, Afternoon, Night)."""
    class Meta:
        ordering = ["start_time"]

    name = models.CharField(max_length=50, unique=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"


class Department(models.Model):
    """Represents a department (Housekeeping, Front Desk, etc.)."""
    class Meta:
        ordering = ["name"]

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class DutyRoster(models.Model):
    """Master roster record for a specific date."""
    class RosterStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    roster_date = models.DateField(unique=True)
    status = models.CharField(max_length=20, choices=RosterStatus.choices, default=RosterStatus.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_rosters",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-roster_date"]

    def __str__(self):
        return f"Roster for {self.roster_date.strftime('%d/%m/%Y')} ({self.get_status_display()})"


class DutyRosterEntry(models.Model):
    """Individual duty assignment in the roster."""
    class EntryStatus(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        CONFIRMED = "confirmed", "Confirmed"
        COMPLETED = "completed", "Completed"
        ABSENT = "absent", "Absent"
        CANCELLED = "cancelled", "Cancelled"

    roster = models.ForeignKey(
        DutyRoster,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="roster_entries",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="roster_entries",
    )
    shift = models.ForeignKey(
        Shift,
        on_delete=models.PROTECT,
        related_name="roster_entries",
    )
    role = models.CharField(max_length=100)
    assigned_duties = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=EntryStatus.choices, default=EntryStatus.ASSIGNED)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_roster_entries",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["shift__start_time", "employee__first_name"]
        unique_together = ["roster", "employee", "shift"]

    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.shift.name} ({self.roster.roster_date})"


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
