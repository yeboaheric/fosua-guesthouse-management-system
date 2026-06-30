from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("guests", "0003_guest_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="guest",
            name="id_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("drivers_license", "Driving Licence"),
                    ("voter_id", "Voter ID"),
                    ("passport", "Passport"),
                    ("national_id", "National ID"),
                    ("other", "Other ID"),
                ],
                max_length=30,
            ),
        ),
    ]
