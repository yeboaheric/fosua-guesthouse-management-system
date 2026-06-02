from django.conf import settings
from django.db import models


class Employee(models.Model):
    TITLE_CHOICES = [
        ("mr", "Mr."),
        ("mrs", "Mrs."),
        ("miss", "Miss"),
        ("sir", "Sir"),
    ]

    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    ]

    POSITION_CHOICES = [
        ("hotel_manager", "Hotel Manager"),
        ("cleaner", "Cleaner"),
        ("security", "Security"),
        ("receptionist", "Receptionist"),
    ]

    MARITAL_STATUS_CHOICES = [
        ("single", "Single"),
        ("married", "Married"),
        ("divorced", "Divorced"),
        ("widowed", "Widowed"),
        ("other", "Other"),
    ]

    RELIGION_CHOICES = [
        ("christian", "Christian"),
        ("muslim", "Muslim"),
    ]

    EMPLOYMENT_STATUS_CHOICES = [
        ("active", "Active"),
        ("annual_leave", "Annual Leave"),
        ("sick_leave", "Sick Leave"),
        ("family_emergency", "Family Emergency"),
        ("suspension", "Suspension"),
        ("terminated", "Terminated"),
    ]

    title = models.CharField(max_length=10, choices=TITLE_CHOICES, blank=True)
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    date_of_birth = models.DateField()
    nationality = models.CharField(max_length=120)
    ghana_card_number = models.CharField(max_length=100, unique=True)
    ghana_card_expiry_date = models.DateField(blank=True, null=True)
    ssnit_number = models.CharField(max_length=100, blank=True)
    contact_number = models.CharField(max_length=40)
    email = models.EmailField(blank=True)
    gps_address = models.CharField(max_length=255, blank=True)
    next_of_kin = models.CharField(max_length=255, blank=True)
    next_of_kin_contact = models.CharField(max_length=40, blank=True)
    next_of_kin_relationship = models.CharField(max_length=120, blank=True)
    start_date = models.DateField()
    termination_date = models.DateField(blank=True, null=True)
    termination_reason = models.TextField(blank=True)
    emergency_contact_number = models.CharField(max_length=40, blank=True)
    position = models.CharField(max_length=20, choices=POSITION_CHOICES)
    employment_status = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_STATUS_CHOICES,
        default="active",
    )
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES)
    ethnic_origin = models.CharField(max_length=120, blank=True)
    religion = models.CharField(max_length=20, choices=RELIGION_CHOICES, blank=True)
    passport_photo = models.ImageField(
        upload_to="employee_photos/",
        blank=True,
        null=True,
        help_text="Upload a passport-style photo.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Employee"
        verbose_name_plural = "Employees"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Rota(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="rota_entries",
    )
    period = models.CharField(max_length=255, blank=True)
    period_start = models.DateField(blank=True, null=True)
    period_end = models.DateField(blank=True, null=True)
    staff_members = models.ManyToManyField(Employee, blank=True, related_name="rotas")
    opening_time = models.TimeField(blank=True, null=True)
    closing_time = models.TimeField(blank=True, null=True)
    shift_rules = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Rota"
        verbose_name_plural = "Rotas"

    def __str__(self):
        if self.employee_id:
            return f"{self.employee} rota"
        if self.period:
            return self.period
        return f"{self.period_start} to {self.period_end}"

    @property
    def operating_hours(self):
        if not self.opening_time or not self.closing_time:
            return "-"
        return f"{self.opening_time.strftime('%I:%M %p')} to {self.closing_time.strftime('%I:%M %p')}"

    @property
    def total_hours(self):
        if not all([self.period_start, self.period_end, self.opening_time, self.closing_time]):
            return 0

        day_count = (self.period_end - self.period_start).days + 1
        opening_minutes = self.opening_time.hour * 60 + self.opening_time.minute
        closing_minutes = self.closing_time.hour * 60 + self.closing_time.minute
        shift_minutes = max(closing_minutes - opening_minutes, 0)
        return round((shift_minutes / 60) * day_count, 2)

    @property
    def daily_hours(self):
        if not self.opening_time or not self.closing_time:
            return 0

        opening_minutes = self.opening_time.hour * 60 + self.opening_time.minute
        closing_minutes = self.closing_time.hour * 60 + self.closing_time.minute
        shift_minutes = max(closing_minutes - opening_minutes, 0)
        return round(shift_minutes / 60, 2)


class UserAccessProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="access_profile",
    )
    dashboard_access = models.BooleanField(default=True)
    reservations_access = models.BooleanField(default=True)
    rooms_access = models.BooleanField(default=True)
    guests_access = models.BooleanField(default=True)
    payments_access = models.BooleanField(default=True)
    services_access = models.BooleanField(default=True)
    housekeeping_access = models.BooleanField(default=True)
    inventory_access = models.BooleanField(default=False)
    pos_access = models.BooleanField(default=True)
    notifications_access = models.BooleanField(default=True)
    analytics_access = models.BooleanField(default=True)
    reports_access = models.BooleanField(default=False)
    settings_access = models.BooleanField(default=False)
    staff_management_access = models.BooleanField(default=False)
    handovers_access = models.BooleanField(default=True)
    users_roles_access = models.BooleanField(default=False)

    class Meta:
        verbose_name = "User Access Profile"
        verbose_name_plural = "User Access Profiles"

    def __str__(self):
        return f"Access profile for {self.user.username}"

    def has_module_access(self, module_name):
        return bool(getattr(self, f"{module_name}_access", False))
