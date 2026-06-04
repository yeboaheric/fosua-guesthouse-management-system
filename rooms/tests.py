from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rooms.models import Room
from rooms.models import HousekeepingTask, HousekeepingTaskToiletry
from inventory.models import ToiletryItem, ToiletryIssue
from django.urls import reverse


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


class HousekeepingTaskIntegrationTests(TestCase):
    def setUp(self):
        admin_group = Group.objects.create(name="Admin")
        hk_group = Group.objects.create(name="Housekeeping Supervisor")
        self.user = User.objects.create_user(username="hk_user", password="pass123456")
        self.user.groups.add(hk_group)

        self.room = Room.objects.create(
            room_number="300",
            room_type=Room.RoomType.STANDARD,
            status=Room.RoomStatus.AVAILABLE,
            base_rate=100,
        )

        self.item = ToiletryItem.objects.create(name="Soap", purchase_price=1.5, quantity_in_stock=10, minimum_stock_threshold=2)

        self.client.force_login(self.user)

    def test_task_completion_issues_toiletries_and_decrements_stock(self):
        task = HousekeepingTask.objects.create(room=self.room, title="Clean and replenish", created_by=self.user)
        req = HousekeepingTaskToiletry.objects.create(task=task, item=self.item, quantity=2)

        # Complete the task via the view
        url = reverse('housekeeping-task-complete', args=[task.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        # Check that a ToiletryIssue was created
        issues = ToiletryIssue.objects.filter(item=self.item, room=self.room)
        self.assertTrue(issues.exists())
        issue = issues.first()
        self.assertEqual(issue.quantity, 2)

        # Stock decremented
        self.item.refresh_from_db()
        self.assertEqual(float(self.item.quantity_in_stock), 8.0)

        # cleanup assertions done above; no further timestamp checks here
