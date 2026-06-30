from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("inventory", "0005_sale_edit_tracking"),
    ]

    operations = [
        migrations.CreateModel(
            name="CashDrawerSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("opening_float", models.DecimalField(decimal_places=2, max_digits=12)),
                ("opening_time", models.DateTimeField(default=django.utils.timezone.now)),
                ("opening_note", models.TextField(blank=True)),
                ("closing_count", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("closing_time", models.DateTimeField(blank=True, null=True)),
                ("expected_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("variance", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("variance_note", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("open", "Open"), ("closed", "Closed")], default="open", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "staff",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="cash_drawer_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-opening_time"],
            },
        ),
        migrations.AddConstraint(
            model_name="cashdrawersession",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "open")),
                fields=("staff",),
                name="unique_open_cash_drawer_session_per_staff",
            ),
        ),
        migrations.AddIndex(
            model_name="cashdrawersession",
            index=models.Index(fields=["status", "opening_time"], name="inventory_c_status_028c6f_idx"),
        ),
        migrations.AddIndex(
            model_name="cashdrawersession",
            index=models.Index(fields=["staff", "opening_time"], name="inventory_c_staff_i_611d8b_idx"),
        ),
    ]
