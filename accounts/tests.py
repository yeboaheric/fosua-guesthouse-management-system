from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from bookings.models import Booking, Payment
from guests.models import Guest
from rooms.models import Room


class DashboardRoutingTests(TestCase):
    def setUp(self):
        self.admin_group = Group.objects.create(name="Admin")
        self.receptionist_group = Group.objects.create(name="Receptionist")

    def test_admin_user_redirected_to_admin_dashboard(self):
        user = User.objects.create_user(username="admin1", password="pass123456")
        user.groups.add(self.admin_group)

        self.client.force_login(user)
        response = self.client.get(reverse("dashboard"))

        self.assertRedirects(response, reverse("admin-dashboard"))

    def test_receptionist_user_redirected_to_reception_dashboard(self):
        user = User.objects.create_user(username="reception1", password="pass123456")
        user.groups.add(self.receptionist_group)

        self.client.force_login(user)
        response = self.client.get(reverse("dashboard"))

        self.assertRedirects(response, reverse("reception-dashboard"))

    def test_admin_reports_access_for_admin_only(self):
        admin_user = User.objects.create_user(username="admin2", password="pass123456")
        admin_user.groups.add(self.admin_group)
        self.client.force_login(admin_user)
        response = self.client.get(reverse("admin-reports"))
        self.assertEqual(response.status_code, 200)

        receptionist_user = User.objects.create_user(
            username="reception2", password="pass123456"
        )
        receptionist_user.groups.add(self.receptionist_group)
        self.client.force_login(receptionist_user)
        response = self.client.get(reverse("admin-reports"))
        self.assertEqual(response.status_code, 403)

    def test_healthz_endpoint_available_without_login(self):
        self.client.logout()
        response = self.client.get(reverse("healthz"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")


class AdminReportExportTests(TestCase):
    def setUp(self):
        self.admin_group = Group.objects.create(name="Admin")
        self.admin_user = User.objects.create_user(username="admin3", password="pass123456")
        self.admin_user.groups.add(self.admin_group)
        self.client.force_login(self.admin_user)

        self.room = Room.objects.create(
            room_number="301",
            room_type=Room.RoomType.STANDARD,
            status=Room.RoomStatus.AVAILABLE,
            base_rate=180,
        )
        self.guest = Guest.objects.create(
            first_name="Efua",
            last_name="Sarpong",
            phone_number="0241111111",
        )
        self.booking = Booking.objects.create(
            guest=self.guest,
            room=self.room,
            check_in=date(2026, 5, 20),
            check_out=date(2026, 5, 22),
            status=Booking.BookingStatus.CONFIRMED,
            total_amount=500,
            created_by=self.admin_user,
        )
        Payment.objects.create(
            booking=self.booking,
            amount=200,
            method=Payment.PaymentMethod.CASH,
            received_by=self.admin_user,
        )

    def test_daily_report_csv_export_returns_csv(self):
        response = self.client.get(
            reverse("admin-reports-export-daily"),
            {"start_date": "2026-05-19", "end_date": "2026-05-23"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("occupied_rooms", response.content.decode())

    def test_balances_report_csv_export_returns_csv(self):
        response = self.client.get(reverse("admin-reports-export-balances"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode()
        self.assertIn("balance_due", content)
        self.assertIn("Efua Sarpong", content)
