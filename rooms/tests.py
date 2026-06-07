from datetime import timedelta
from io import BytesIO

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from rooms.models import HousekeepingItemLog, Room


class RoomCategoryTests(TestCase):
    def setUp(self):
        admin_group = Group.objects.create(name="Admin")
        self.user = User.objects.create_user(username="admin_rooms", password="pass123456")
        self.user.groups.add(admin_group)
        Room.objects.create(
            room_number="101",
            room_type=Room.RoomType.DELUXE,
            status=Room.RoomStatus.AVAILABLE,
            base_rate=320,
        )
        Room.objects.create(
            room_number="109",
            room_type=Room.RoomType.STANDARD,
            status=Room.RoomStatus.CLEANING,
            base_rate=180,
        )

    def test_room_list_shows_standard_and_deluxe_categories(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("room-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Deluxe Rooms")
        self.assertContains(response, "Standard Rooms")
        self.assertContains(response, "Cleaning In Progress")


class RoomTimestampTests(TestCase):
    def test_room_status_timestamps_only_change_when_status_changes(self):
        room = Room.objects.create(
            room_number="210",
            room_type=Room.RoomType.STANDARD,
            status=Room.RoomStatus.AVAILABLE,
            base_rate=200,
        )

        original_started = room.status_started_at
        original_changed = room.last_status_changed_at

        room.base_rate = 250
        room.save()
        room.refresh_from_db()
        self.assertEqual(room.status_started_at, original_started)
        self.assertGreater(room.last_status_changed_at, original_changed)


class HousekeepingUsageLoggerTests(TestCase):
    def setUp(self):
        admin_group = Group.objects.create(name="Admin")
        self.user = User.objects.create_user(username="housekeeping_admin", password="pass123456")
        self.user.groups.add(admin_group)
        self.room = Room.objects.create(
            room_number="300",
            room_type=Room.RoomType.STANDARD,
            status=Room.RoomStatus.AVAILABLE,
            base_rate=100,
        )
        self.client.force_login(self.user)

    def test_create_usage_entry(self):
        response = self.client.post(
            f"{reverse('housekeeping-dashboard')}?report=daily",
            {
                "item_name": "Bath Soap",
                "initial_quantity": "12.000",
                "quantity_used": "2.000",
                "quantity_in_stock": "10.000",
                "low_stock_threshold": "3.000",
                "unit": "bars",
                "room": self.room.pk,
                "used_at": timezone.localtime(timezone.now()).strftime("%Y-%m-%dT%H:%M"),
                "notes": "Restocked bathroom",
            },
        )
        self.assertEqual(response.status_code, 302)
        entry = HousekeepingItemLog.objects.get(item_name="Bath Soap")
        self.assertEqual(str(entry.initial_quantity), "12.000")
        self.assertEqual(str(entry.quantity_used), "2.000")
        self.assertEqual(str(entry.quantity_in_stock), "10.000")
        self.assertEqual(str(entry.low_stock_threshold), "3.000")
        self.assertEqual(entry.room, self.room)
        self.assertEqual(entry.created_by, self.user)

    def test_edit_and_delete_usage_entry(self):
        entry = HousekeepingItemLog.objects.create(
            item_name="Towel",
            initial_quantity="8.000",
            quantity_used="4.000",
            quantity_in_stock="4.000",
            unit="sheets",
            room=self.room,
            used_at=timezone.now(),
            created_by=self.user,
        )

        edit_response = self.client.post(
            f"{reverse('housekeeping-log-edit', args=[entry.pk])}?report=weekly",
            {
                "item_name": "Towel",
                "initial_quantity": "9.000",
                "quantity_used": "5.000",
                "quantity_in_stock": "4.000",
                "low_stock_threshold": "2.000",
                "unit": "sheets",
                "room": self.room.pk,
                "used_at": timezone.localtime(entry.used_at).strftime("%Y-%m-%dT%H:%M"),
                "notes": "Updated count",
            },
        )
        self.assertEqual(edit_response.status_code, 302)
        entry.refresh_from_db()
        self.assertEqual(str(entry.quantity_used), "5.000")
        self.assertEqual(str(entry.initial_quantity), "9.000")
        self.assertEqual(str(entry.quantity_in_stock), "4.000")
        self.assertEqual(entry.notes, "Updated count")

        delete_response = self.client.post(
            f"{reverse('housekeeping-log-delete', args=[entry.pk])}?report=weekly"
        )
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(HousekeepingItemLog.objects.filter(pk=entry.pk).exists())

    def test_daily_report_and_excel_export(self):
        now = timezone.now()
        HousekeepingItemLog.objects.create(
            item_name="Bath Soap",
            initial_quantity="10.000",
            quantity_used="2.000",
            quantity_in_stock="8.000",
            unit="bars",
            room=self.room,
            used_at=now,
            created_by=self.user,
        )
        HousekeepingItemLog.objects.create(
            item_name="Bath Soap",
            initial_quantity="8.000",
            quantity_used="1.000",
            quantity_in_stock="7.000",
            unit="bars",
            room=self.room,
            used_at=now - timedelta(hours=1),
            created_by=self.user,
        )
        HousekeepingItemLog.objects.create(
            item_name="Bed Sheet",
            initial_quantity="12.000",
            quantity_used="3.000",
            quantity_in_stock="9.000",
            unit="sheets",
            room=self.room,
            used_at=now - timedelta(days=2),
            created_by=self.user,
        )

        response = self.client.get(f"{reverse('housekeeping-dashboard')}?report=daily")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Daily report")
        self.assertContains(response, "Bath Soap")
        self.assertEqual(
            [row["item_name"] for row in response.context["report_summary_rows"]],
            ["Bath Soap"],
        )
        self.assertContains(response, "Total initial stock")
        self.assertContains(response, "Total items currently in stock")
        self.assertEqual(str(response.context["summary_total_items_in_stock"]), "17.000")

        export_response = self.client.get(reverse("housekeeping-report-export", args=["daily"]))
        self.assertEqual(export_response.status_code, 200)
        self.assertEqual(
            export_response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn("housekeeping-report-daily-", export_response["Content-Disposition"])

        workbook = load_workbook(BytesIO(export_response.content))
        worksheet = workbook.active
        self.assertEqual(worksheet["A4"].value, "Item Name")
        self.assertEqual(worksheet["B4"].value, "Total Initial Qty")
        self.assertEqual(worksheet["A5"].value, "Bath Soap")
        self.assertEqual(worksheet["B5"].value, 18)
        self.assertEqual(worksheet["C5"].value, 3)
        self.assertEqual(worksheet["D5"].value, 15)
        self.assertEqual(worksheet[f"A{worksheet.max_row}"].value, "TOTALS")

    def test_low_stock_alert_uses_default_and_custom_thresholds(self):
        now = timezone.now()
        HousekeepingItemLog.objects.create(
            item_name="Glass Cleaner",
            initial_quantity="10.000",
            quantity_used="8.500",
            quantity_in_stock="1.500",
            unit="litres",
            room=self.room,
            used_at=now,
            created_by=self.user,
        )
        HousekeepingItemLog.objects.create(
            item_name="Laundry Soap",
            initial_quantity="30.000",
            quantity_used="20.000",
            quantity_in_stock="10.000",
            low_stock_threshold="12.000",
            unit="bars",
            room=self.room,
            used_at=now,
            created_by=self.user,
        )

        response = self.client.get(reverse("housekeeping-dashboard"))
        self.assertEqual(response.status_code, 200)
        low_stock_names = [entry.item_name for entry in response.context["low_stock_entries"]]
        self.assertEqual(low_stock_names, ["Glass Cleaner", "Laundry Soap"])
