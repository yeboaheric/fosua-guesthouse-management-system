from datetime import date, time, timedelta

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking, EventBooking, EventPayment, Payment
from guests.models import Guest
from rooms.models import Room


class BookingValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff1", password="pass123456")
        self.room = Room.objects.create(
            room_number="101",
            room_type=Room.RoomType.STANDARD,
            status=Room.RoomStatus.AVAILABLE,
            base_rate=100,
        )
        self.guest = Guest.objects.create(
            first_name="Kojo",
            last_name="Mensah",
            phone_number="0240000000",
        )

    def test_check_out_must_be_after_check_in(self):
        booking = Booking(
            guest=self.guest,
            room=self.room,
            check_in=date(2026, 6, 15),
            check_out=date(2026, 6, 15),
            status=Booking.BookingStatus.CONFIRMED,
            created_by=self.user,
        )

        with self.assertRaises(ValidationError):
            booking.save()

    def test_overlapping_booking_for_same_room_is_blocked(self):
        Booking.objects.create(
            guest=self.guest,
            room=self.room,
            check_in=date(2026, 6, 10),
            check_out=date(2026, 6, 12),
            status=Booking.BookingStatus.CONFIRMED,
            created_by=self.user,
        )

        new_guest = Guest.objects.create(
            first_name="Ama",
            last_name="Boateng",
            phone_number="0550000000",
        )
        overlapping_booking = Booking(
            guest=new_guest,
            room=self.room,
            check_in=date(2026, 6, 11),
            check_out=date(2026, 6, 13),
            status=Booking.BookingStatus.PENDING,
            created_by=self.user,
        )

        with self.assertRaises(ValidationError):
            overlapping_booking.save()

    def test_non_overlapping_booking_is_allowed(self):
        Booking.objects.create(
            guest=self.guest,
            room=self.room,
            check_in=date(2026, 6, 10),
            check_out=date(2026, 6, 12),
            status=Booking.BookingStatus.CONFIRMED,
            created_by=self.user,
        )

        new_guest = Guest.objects.create(
            first_name="Yaw",
            last_name="Asare",
            phone_number="0200000000",
        )
        booking = Booking(
            guest=new_guest,
            room=self.room,
            check_in=date(2026, 6, 12),
            check_out=date(2026, 6, 14),
            status=Booking.BookingStatus.PENDING,
            created_by=self.user,
        )
        booking.save()

        self.assertIsNotNone(booking.pk)


class BookingWorkflowTests(TestCase):
    def setUp(self):
        self.reception_role = Group.objects.create(name="Receptionist")
        self.user = User.objects.create_user(username="reception1", password="pass123456")
        self.user.groups.add(self.reception_role)
        self.room = Room.objects.create(
            room_number="201",
            room_type=Room.RoomType.DELUXE,
            status=Room.RoomStatus.AVAILABLE,
            base_rate=200,
        )
        self.room_two = Room.objects.create(
            room_number="202",
            room_type=Room.RoomType.DELUXE,
            status=Room.RoomStatus.AVAILABLE,
            base_rate=220,
        )
        self.guest = Guest.objects.create(
            first_name="Akua",
            last_name="Owusu",
            phone_number="0270000000",
        )
        self.other_guest = Guest.objects.create(
            first_name="Yaw",
            last_name="Asare",
            phone_number="0200000000",
        )
        self.booking = Booking.objects.create(
            guest=self.guest,
            room=self.room,
            check_in=date(2026, 7, 1),
            check_out=date(2026, 7, 3),
            status=Booking.BookingStatus.CONFIRMED,
            created_by=self.user,
        )
        self.booking_two = Booking.objects.create(
            guest=self.other_guest,
            room=self.room_two,
            check_in=date(2026, 7, 1),
            check_out=date(2026, 7, 4),
            status=Booking.BookingStatus.PENDING,
            created_by=self.user,
        )

    def test_check_in_updates_booking_and_room_status(self):
        original_started = self.room.status_started_at
        original_changed = self.room.last_status_changed_at
        self.client.force_login(self.user)
        response = self.client.post(reverse("booking-check-in", args=[self.booking.pk]))
        self.assertRedirects(response, reverse("booking-list"))

        self.booking.refresh_from_db()
        self.room.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.BookingStatus.CHECKED_IN)
        self.assertEqual(self.room.status, Room.RoomStatus.OCCUPIED)
        self.assertGreater(self.room.status_started_at, original_started)
        self.assertGreater(self.room.last_status_changed_at, original_changed)

    def test_check_out_updates_booking_and_room_status(self):
        self.booking.status = Booking.BookingStatus.CHECKED_IN
        self.booking.save()
        self.room.status = Room.RoomStatus.OCCUPIED
        self.room.save()
        original_started = self.room.status_started_at
        original_changed = self.room.last_status_changed_at

        self.client.force_login(self.user)
        response = self.client.post(reverse("booking-check-out", args=[self.booking.pk]))
        self.assertRedirects(response, reverse("booking-list"))

        self.booking.refresh_from_db()
        self.room.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.BookingStatus.CHECKED_OUT)
        self.assertEqual(self.room.status, Room.RoomStatus.AVAILABLE)
        self.assertGreater(self.room.status_started_at, original_started)
        self.assertGreater(self.room.last_status_changed_at, original_changed)

    def test_record_payment_updates_booking_balance(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("booking-payments", args=[self.booking.pk]),
            {
                "amount": "150.00",
                "method": Payment.PaymentMethod.CASH,
                "reference": "RCPT-001",
                "notes": "Deposit",
            },
        )
        self.assertRedirects(response, reverse("booking-payments", args=[self.booking.pk]))

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.amount_paid, 150)
        self.assertEqual(self.booking.balance_due, 250)

    def test_operations_overview_access_and_counts(self):
        self.room.status = Room.RoomStatus.CLEANING
        self.room.save()
        self.client.force_login(self.user)
        response = self.client.get(reverse("operations-overview"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Operations Overview")
        self.assertContains(response, "Cleaning")

    def test_create_booking_for_multiple_rooms(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("booking-create"),
            {
                "guest": self.guest.pk,
                "rooms": [self.room.pk, self.room_two.pk],
                "check_in": "2026-07-10",
                "check_in_time": "14:00",
                "check_out": "2026-07-12",
                "check_out_time": "11:00",
                "adults": 2,
                "children": 0,
                "status": Booking.BookingStatus.PENDING,
                "notes": "Family reservation",
                "total_amount": "",
            },
        )
        self.assertRedirects(response, reverse("booking-list"))
        created = Booking.objects.filter(
            guest=self.guest,
            check_in=date(2026, 7, 10),
            check_out=date(2026, 7, 12),
        )
        self.assertEqual(created.count(), 2)
        for booking in created:
            self.assertEqual(booking.check_in_time, time(14, 0))
            self.assertEqual(booking.check_out_time, time(11, 0))

    def test_booking_default_check_in_out_times_are_assigned(self):
        booking = Booking.objects.create(
            guest=self.guest,
            room=self.room,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            status=Booking.BookingStatus.CONFIRMED,
            created_by=self.user,
        )
        self.assertEqual(booking.check_in_time, time(14, 0))
        self.assertEqual(booking.check_out_time, time(11, 0))

    def test_booking_list_filters_by_status_and_search(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("booking-list"),
            {"status": Booking.BookingStatus.CONFIRMED, "q": "Akua"},
        )

        self.assertEqual(response.status_code, 200)
        bookings = list(response.context["bookings"])
        self.assertEqual(len(bookings), 1)
        self.assertEqual(bookings[0].pk, self.booking.pk)
        self.assertContains(response, "Akua Owusu")
        self.assertNotContains(response, "Yaw Asare")


class EventBookingWorkflowTests(TestCase):
    def setUp(self):
        self.reception_role = Group.objects.create(name="Receptionist")
        self.user = User.objects.create_user(username="reception2", password="pass123456")
        self.user.groups.add(self.reception_role)
        self.guest = Guest.objects.create(
            first_name="Esi",
            last_name="Owusu",
            phone_number="0260000000",
        )
        base = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        self.event_booking = EventBooking.objects.create(
            guest=self.guest,
            event_space_name="Main Event Space",
            event_title="Community Meeting",
            purpose="Monthly local association meeting",
            expected_guests=50,
            event_start=base + timedelta(days=2, hours=9),
            event_end=base + timedelta(days=2, hours=13),
            status=EventBooking.EventBookingStatus.PENDING,
            created_by=self.user,
        )

    def test_event_booking_overlap_blocked_for_same_space(self):
        overlap = EventBooking(
            guest=self.guest,
            event_space_name="Main Event Space",
            event_title="Wedding Prep",
            purpose="Decoration and setup",
            expected_guests=30,
            event_start=self.event_booking.event_start + timedelta(hours=1),
            event_end=self.event_booking.event_end + timedelta(hours=1),
            status=EventBooking.EventBookingStatus.CONFIRMED,
            created_by=self.user,
        )
        with self.assertRaises(ValidationError):
            overlap.save()

    def test_event_booking_start_action_updates_status(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("event-booking-start", args=[self.event_booking.pk]))
        self.assertRedirects(response, reverse("event-booking-list"))
        self.event_booking.refresh_from_db()
        self.assertEqual(self.event_booking.status, EventBooking.EventBookingStatus.IN_PROGRESS)

    def test_event_payment_updates_balance(self):
        self.client.force_login(self.user)
        self.event_booking.total_amount = 1000
        self.event_booking.save()
        response = self.client.post(
            reverse("event-booking-payments", args=[self.event_booking.pk]),
            {
                "amount": "350.00",
                "method": EventPayment.PaymentMethod.CASH,
                "reference": "EVT-001",
                "notes": "Deposit",
            },
        )
        self.assertRedirects(
            response,
            reverse("event-booking-payments", args=[self.event_booking.pk]),
        )
        self.event_booking.refresh_from_db()
        self.assertEqual(self.event_booking.amount_paid, 350)
        self.assertEqual(self.event_booking.balance_due, 650)

    def test_event_booking_pages_load(self):
        self.client.force_login(self.user)
        list_response = self.client.get(reverse("event-booking-list"))
        create_response = self.client.get(reverse("event-booking-create"))
        payments_response = self.client.get(
            reverse("event-booking-payments", args=[self.event_booking.pk])
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(payments_response.status_code, 200)
