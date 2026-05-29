from django.db import models


class Employee(models.Model):
    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    ]

    MARITAL_STATUS_CHOICES = [
        ("single", "Single"),
        ("married", "Married"),
        ("divorced", "Divorced"),
        ("widowed", "Widowed"),
        ("other", "Other"),
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
    position = models.CharField(max_length=120)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES)
    ethnic_origin = models.CharField(max_length=120, blank=True)
    religion = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Employee"
        verbose_name_plural = "Employees"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
