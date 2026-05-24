from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from shifts.models import ShiftHandover, ShiftHandoverUpdate


class ShiftHandoverWorkflowTests(TestCase):
    def setUp(self):
        receptionist_group = Group.objects.create(name="Receptionist")
        self.reception_a = User.objects.create_user(
            username="reception_a",
            password="pass123456",
        )
        self.reception_b = User.objects.create_user(
            username="reception_b",
            password="pass123456",
        )
        self.reception_a.groups.add(receptionist_group)
        self.reception_b.groups.add(receptionist_group)

    def test_reception_can_create_handover(self):
        self.client.force_login(self.reception_a)
        start = timezone.localtime() - timedelta(hours=8)
        end = timezone.localtime()
        response = self.client.post(
            reverse("handover-create"),
            {
                "started_at": start.strftime("%Y-%m-%dT%H:%M"),
                "ended_at": end.strftime("%Y-%m-%dT%H:%M"),
                "summary": "Cash reconciled and all arrivals confirmed.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ShiftHandover.objects.count(), 1)

    def test_next_reception_can_add_update_only(self):
        handover = ShiftHandover.objects.create(
            started_at=timezone.localtime() - timedelta(hours=8),
            ended_at=timezone.localtime(),
            prepared_by=self.reception_a,
            summary="Initial shift handover.",
        )
        self.client.force_login(self.reception_b)
        response = self.client.post(
            reverse("handover-detail", args=[handover.pk]),
            {"note": "Received. Late arrival guest checked in at 20:15."},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ShiftHandoverUpdate.objects.count(), 1)
        handover.refresh_from_db()
        self.assertEqual(handover.summary, "Initial shift handover.")
