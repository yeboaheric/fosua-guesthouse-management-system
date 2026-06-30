from django.db import models

from accounts.models import StatusTrackingMixin


class Guest(StatusTrackingMixin, models.Model):
    class Title(models.TextChoices):
        MR = "mr", "Mr."
        MRS = "mrs", "Mrs."
        MISS = "miss", "Miss"
        SIR = "sir", "Sir"

    class OtherIdType(models.TextChoices):
        DRIVERS_LICENSE = "drivers_license", "Driving Licence"
        VOTER_ID = "voter_id", "Voter ID"
        PASSPORT = "passport", "Passport"
        NATIONAL_ID = "national_id", "National ID"
        OTHER = "other", "Other ID"

    title = models.CharField(max_length=10, choices=Title.choices, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    id_type = models.CharField(
        max_length=30,
        choices=OtherIdType.choices,
        blank=True,
    )
    id_number = models.CharField(max_length=50, blank=True)
    ghana_card_number = models.CharField(max_length=50, blank=True)
    ghana_card_expiry_date = models.DateField(blank=True, null=True)
    digital_address = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("inactive", "Inactive"),
            ("blacklisted", "Blacklisted"),
            ("no_show", "No-show"),
        ],
        default="active",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
