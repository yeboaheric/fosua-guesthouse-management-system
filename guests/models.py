from django.db import models


class Guest(models.Model):
    class Title(models.TextChoices):
        MR = "mr", "Mr."
        MRS = "mrs", "Mrs."
        MISS = "miss", "Miss"
        SIR = "sir", "Sir"

    title = models.CharField(max_length=10, choices=Title.choices, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    id_number = models.CharField(max_length=50, blank=True)
    ghana_card_number = models.CharField(max_length=50, blank=True)
    ghana_card_expiry_date = models.DateField(blank=True, null=True)
    digital_address = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
