from accounts.models import Employee, Notification, Rota, RolePermission, UserAccessProfile
from accounts.permissions import user_has_permission
from bookings.models import Booking, EventBooking, EventPayment, Payment
from datetime import date, time, timedelta
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from guests.models import Guest
from rooms.models import Room
from django.utils import timezone


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

    def test_users_roles_center_access_for_admin_only(self):
        admin_user = User.objects.create_user(username="admin-users", password="pass123456")
        admin_user.groups.add(self.admin_group)
        self.client.force_login(admin_user)
        response = self.client.get(reverse("users-roles-center"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Users and roles")
        self.assertContains(response, "Permissions")

        receptionist_user = User.objects.create_user(
            username="reception-users", password="pass123456"
        )
        receptionist_user.groups.add(self.receptionist_group)
        self.client.force_login(receptionist_user)
        response = self.client.get(reverse("users-roles-center"))
        self.assertEqual(response.status_code, 403)

    def test_receptionist_module_access_can_be_restricted(self):
        blocked_group = Group.objects.create(name="Blocked Reception")
        RolePermission.objects.create(
            role=blocked_group,
            module="rooms",
            can_view=True,
        )
        user = User.objects.create_user(username="reception-blocked", password="pass123456")
        user.groups.add(blocked_group)
        UserAccessProfile.objects.create(
            user=user,
            dashboard_access=True,
            reservations_access=False,
            rooms_access=True,
            guests_access=True,
            payments_access=True,
            services_access=True,
            housekeeping_access=True,
            notifications_access=True,
            analytics_access=True,
            reports_access=False,
            settings_access=False,
            staff_management_access=False,
            handovers_access=True,
            users_roles_access=False,
        )

        self.assertTrue(
            self.client.post(
                reverse("login"),
                {"username": "reception-blocked", "password": "pass123456"},
            ).status_code in {200, 302}
        )
        response = self.client.get(reverse("booking-list"))
        self.assertEqual(response.status_code, 403)

        response = self.client.get(reverse("room-list"))
        self.assertEqual(response.status_code, 200)

    def test_notifications_center_generates_arrival_reminders(self):
        user = User.objects.create_user(username="notify1", password="pass123456")
        user.groups.add(self.receptionist_group)
        UserAccessProfile.objects.create(
            user=user,
            dashboard_access=True,
            reservations_access=True,
            rooms_access=True,
            guests_access=True,
            payments_access=True,
            services_access=True,
            housekeeping_access=True,
            notifications_access=True,
            analytics_access=True,
            reports_access=False,
            settings_access=False,
            staff_management_access=False,
            handovers_access=True,
            users_roles_access=False,
        )
        room = Room.objects.create(
            room_number="501",
            room_type=Room.RoomType.STANDARD,
            status=Room.RoomStatus.AVAILABLE,
            base_rate=120,
        )
        guest = Guest.objects.create(
            first_name="Nana",
            last_name="Yeboah",
            phone_number="0245555555",
        )
        now = timezone.localtime()
        check_in_time = (now + timedelta(minutes=30)).time().replace(second=0, microsecond=0)
        Booking.objects.create(
            guest=guest,
            room=room,
            check_in=now.date(),
            check_in_time=check_in_time,
            check_out=now.date() + timedelta(days=1),
            status=Booking.BookingStatus.CONFIRMED,
            created_by=user,
        )
        self.client.force_login(user)
        response = self.client.get(reverse("notifications-center"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upcoming check-in")
        self.assertEqual(Notification.objects.filter(user=user).count(), 1)


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


class RotaViewTests(TestCase):
    def setUp(self):
        self.admin_group = Group.objects.create(name="Admin")
        self.admin_user = User.objects.create_user(username="admin4", password="pass123456")
        self.admin_user.groups.add(self.admin_group)
        self.client.force_login(self.admin_user)

        self.employee = Employee.objects.create(
            title="mr",
            first_name="Kwame",
            last_name="Mensah",
            date_of_birth=date(1995, 6, 1),
            nationality="Ghanaian",
            ghana_card_number="GHA-999999999-9",
            contact_number="0249999999",
            start_date=date(2025, 1, 1),
            position="receptionist",
            employment_status="active",
            gender="male",
            marital_status="single",
        )
        self.rota = Rota.objects.create(
            employee=self.employee,
            period="Kwame Mensah weekly duty roster",
            period_start=date(2026, 5, 18),
            period_end=date(2026, 5, 24),
            opening_time=time(8, 0),
            closing_time=time(16, 0),
            shift_rules="Keep the front desk fully covered and hand over notes each evening.",
        )
        self.rota.staff_members.set([self.employee])

    def test_rota_list_supports_range_filtering(self):
        response = self.client.get(
            reverse("hr-rota-list"),
            {"period": "month", "date": "2026-05-20", "q": "Kwame"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kwame Mensah")
        self.assertContains(response, "Daily roster report")

    def test_rota_detail_shows_daily_breakdown(self):
        response = self.client.get(reverse("hr-rota-detail", args=[self.rota.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Day-by-day employee account")
        self.assertContains(response, "Monday")
        self.assertContains(response, "8.00")


class CustomRolePermissionTests(TestCase):
    def setUp(self):
        self.role = Group.objects.create(name="Stock Specialist")
        RolePermission.objects.create(
            role=self.role,
            module="inventory",
            can_view=True,
            can_create=True,
            can_edit=True,
            can_delete=False,
            can_approve=False,
            can_export=True,
            can_print=True,
            can_manage=False,
        )
        self.user = User.objects.create_user(username="stockuser", password="pass123456")
        self.user.groups.add(self.role)
        self.client.force_login(self.user)

    def test_custom_role_can_access_inventory_but_not_user_management(self):
        self.assertTrue(user_has_permission(self.user, "inventory", "view"))

        response = self.client.get(reverse("inventory-dashboard"))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse("users-roles-center"))
        self.assertEqual(response.status_code, 403)


class CenterFilterTests(TestCase):
    def setUp(self):
        self.admin_group = Group.objects.create(name="Admin")
        self.user = User.objects.create_user(username="admin5", password="pass123456")
        self.user.groups.add(self.admin_group)
        self.client.force_login(self.user)

        self.room = Room.objects.create(
            room_number="401",
            room_type=Room.RoomType.STANDARD,
            status=Room.RoomStatus.AVAILABLE,
            base_rate=150,
            notes="Near the courtyard",
        )
        self.cleaning_room = Room.objects.create(
            room_number="402",
            room_type=Room.RoomType.DELUXE,
            status=Room.RoomStatus.CLEANING,
            base_rate=250,
            notes="Deep clean scheduled",
        )
        self.guest = Guest.objects.create(
            first_name="Abena",
            last_name="Danso",
            phone_number="0243333333",
            ghana_card_number="GHA-222222222-2",
        )
        self.event_guest = Guest.objects.create(
            first_name="Kwesi",
            last_name="Appiah",
            phone_number="0553333333",
        )
        self.booking = Booking.objects.create(
            guest=self.guest,
            room=self.room,
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 3),
            status=Booking.BookingStatus.CONFIRMED,
            created_by=self.user,
        )
        self.event_booking = EventBooking.objects.create(
            guest=self.event_guest,
            event_space_name="Main Event Space",
            event_title="Annual Gala",
            purpose="Company celebration",
            expected_guests=80,
            event_start=timezone.localtime().replace(day=5, hour=10, minute=0, second=0, microsecond=0),
            event_end=timezone.localtime().replace(day=5, hour=15, minute=0, second=0, microsecond=0),
            status=EventBooking.EventBookingStatus.CONFIRMED,
            created_by=self.user,
        )
        self.cancelled_event = EventBooking.objects.create(
            guest=self.event_guest,
            event_space_name="Main Event Space",
            event_title="Cancelled Workshop",
            purpose="Training session",
            expected_guests=20,
            event_start=timezone.localtime().replace(day=8, hour=9, minute=0, second=0, microsecond=0),
            event_end=timezone.localtime().replace(day=8, hour=11, minute=0, second=0, microsecond=0),
            status=EventBooking.EventBookingStatus.CANCELLED,
            created_by=self.user,
        )
        self.room_payment = Payment.objects.create(
            booking=self.booking,
            amount=100,
            method=Payment.PaymentMethod.CASH,
            reference="ROOM-001",
            received_by=self.user,
        )
        self.event_payment = EventPayment.objects.create(
            event_booking=self.event_booking,
            amount=300,
            method=EventPayment.PaymentMethod.MOBILE_MONEY,
            reference="EVENT-001",
            received_by=self.user,
        )

    def test_guest_list_filter_returns_matching_guest(self):
        response = self.client.get(reverse("guest-list"), {"q": "Abena"})
        self.assertEqual(response.status_code, 200)
        guests = list(response.context["guests"])
        self.assertEqual(len(guests), 1)
        self.assertEqual(guests[0].first_name, "Abena")

    def test_booking_list_filter_combines_status_and_query(self):
        response = self.client.get(
            reverse("booking-list"),
            {"status": Booking.BookingStatus.CONFIRMED, "q": "401"},
        )
        self.assertEqual(response.status_code, 200)
        bookings = list(response.context["bookings"])
        self.assertEqual(len(bookings), 1)
        self.assertEqual(bookings[0].room.room_number, "401")

    def test_payments_center_filters_by_method_and_scope(self):
        response = self.client.get(
            reverse("payments-center"),
            {"method": Payment.PaymentMethod.CASH, "scope": "room", "q": "ROOM-001"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["room_payments"]), [self.room_payment])
        self.assertEqual(list(response.context["event_payments"]), [])

    def test_services_center_filters_by_status_and_query(self):
        response = self.client.get(
            reverse("services-center"),
            {"status": EventBooking.EventBookingStatus.CONFIRMED, "q": "Annual"},
        )
        self.assertEqual(response.status_code, 200)
        events = list(response.context["events"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].pk, self.event_booking.pk)

    def test_housekeeping_center_redirects_to_housekeeping_dashboard(self):
        response = self.client.get(
            reverse("housekeeping-center"),
            {"report": "weekly"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            f"{reverse('housekeeping-dashboard')}?report=weekly",
        )


class PermissionSnapshotTests(TestCase):
    def test_permission_changes_take_effect_after_logout_and_signin(self):
        role = Group.objects.create(name="Temp Reception")
        RolePermission.objects.create(
            role=role,
            module="reservations",
            can_view=True,
            can_create=True,
        )
        user = User.objects.create_user(username="temp_reception", password="pass123456")
        user.groups.add(role)

        self.assertTrue(
            self.client.post(
                reverse("login"),
                {"username": "temp_reception", "password": "pass123456"},
            ).status_code in {200, 302}
        )
        response = self.client.get(reverse("booking-list"))
        self.assertEqual(response.status_code, 200)

        permission = RolePermission.objects.get(role=role, module="reservations")
        permission.can_view = False
        permission.can_create = False
        permission.save(update_fields=["can_view", "can_create", "updated_at"])

        response = self.client.get(reverse("booking-list"))
        self.assertEqual(response.status_code, 200)

        self.client.logout()
        self.assertTrue(
            self.client.post(
                reverse("login"),
                {"username": "temp_reception", "password": "pass123456"},
            ).status_code in {200, 302}
        )
        response = self.client.get(reverse("booking-list"))
        self.assertEqual(response.status_code, 403)


class UserDeletionTests(TestCase):
    def test_delete_user_removes_account(self):
        admin_group = Group.objects.create(name="Admin")
        receptionist_group = Group.objects.create(name="Receptionist")
        admin = User.objects.create_user(username="delete_admin", password="pass123456")
        admin.groups.add(admin_group)
        target = User.objects.create_user(username="delete_target", password="pass123456")
        target.groups.add(receptionist_group)
        UserAccessProfile.objects.create(user=target, dashboard_access=True)
        self.client.force_login(admin)

        response = self.client.post(
            reverse("users-roles-center"),
            {"action": "delete_user", "user_id": target.pk},
        )

        self.assertRedirects(response, reverse("users-roles-center"))
        self.assertFalse(User.objects.filter(username="delete_target").exists())


class PasswordResetViewsTests(TestCase):
    def test_password_reset_page_is_available(self):
        response = self.client.get(reverse("password_reset"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reset your password")
