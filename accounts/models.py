from django.db import models


class Employee(models.Model):
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

    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    date_of_birth = models.DateField()
    nationality = models.CharField(max_length=120)
    ghana_card_number = models.CharField(max_length=100, unique=True)
    contact_number = models.CharField(max_length=40)
    email = models.EmailField(blank=True)
    gps_address = models.CharField(max_length=255, blank=True)
    next_of_kin = models.CharField(max_length=255, blank=True)
    start_date = models.DateField()
    termination_date = models.DateField(blank=True, null=True)
    emergency_contact_number = models.CharField(max_length=40, blank=True)
    position = models.CharField(max_length=20, choices=POSITION_CHOICES)
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
        if self.period:
            return self.period
        return f"{self.period_start} to {self.period_end}"

    @property
    def operating_hours(self):
        return f"{self.opening_time.strftime('%I:%M %p')} to {self.closing_time.strftime('%I:%M %p')}"
