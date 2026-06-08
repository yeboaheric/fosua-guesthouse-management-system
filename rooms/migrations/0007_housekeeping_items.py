import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def create_housekeeping_items(apps, schema_editor):
    HousekeepingItem = apps.get_model("rooms", "HousekeepingItem")
    HousekeepingItemLog = apps.get_model("rooms", "HousekeepingItemLog")

    latest_entries = {}
    for log in HousekeepingItemLog.objects.order_by("item_name", "unit", "-used_at", "-created_at", "-pk"):
        key = (log.item_name.strip(), log.unit.strip())
        latest_entries.setdefault(key, log)

    item_ids = {}
    for key, log in latest_entries.items():
        item = HousekeepingItem.objects.create(
            name=key[0],
            initial_quantity=log.initial_quantity,
            quantity_in_stock=log.quantity_in_stock,
            low_stock_threshold=log.low_stock_threshold,
            unit=key[1],
            created_by=log.created_by,
        )
        item_ids[key] = item.pk

    for log in HousekeepingItemLog.objects.all():
        key = (log.item_name.strip(), log.unit.strip())
        log.item_id = item_ids[key]
        log.save(update_fields=["item"])


def delete_housekeeping_items(apps, schema_editor):
    HousekeepingItem = apps.get_model("rooms", "HousekeepingItem")
    HousekeepingItemLog = apps.get_model("rooms", "HousekeepingItemLog")
    HousekeepingItemLog.objects.update(item=None)
    HousekeepingItem.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("rooms", "0006_housekeeping_item_stock_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="HousekeepingItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160, unique=True)),
                (
                    "initial_quantity",
                    models.DecimalField(
                        decimal_places=3,
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(0.001)],
                    ),
                ),
                (
                    "quantity_in_stock",
                    models.DecimalField(
                        decimal_places=3,
                        default=0,
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                (
                    "low_stock_threshold",
                    models.DecimalField(
                        blank=True,
                        decimal_places=3,
                        help_text="Optional custom alert threshold for this item.",
                        max_digits=12,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                ("unit", models.CharField(max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="housekeeping_items",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.AddIndex(
            model_name="housekeepingitem",
            index=models.Index(fields=["name"], name="rooms_house_name_233c60_idx"),
        ),
        migrations.AddField(
            model_name="housekeepingitemlog",
            name="item",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="usage_logs",
                to="rooms.housekeepingitem",
            ),
        ),
        migrations.RunPython(create_housekeeping_items, delete_housekeeping_items),
        migrations.AlterField(
            model_name="housekeepingitemlog",
            name="item",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="usage_logs",
                to="rooms.housekeepingitem",
            ),
        ),
    ]
