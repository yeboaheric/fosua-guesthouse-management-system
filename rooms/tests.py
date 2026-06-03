from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rooms.models import Room


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

        room.status = Room.RoomStatus.CLEANING
        room.save()
        room.refresh_from_db()
        self.assertGreater(room.status_started_at, original_started)
        self.assertGreater(room.last_status_changed_at, original_changed)
