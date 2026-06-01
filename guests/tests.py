from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from guests.forms import GuestForm
from guests.models import Guest


class GuestFormTests(TestCase):
    def test_guest_form_hides_id_number_and_address_fields(self):
        form = GuestForm()
        self.assertNotIn("id_number", form.fields)
        self.assertNotIn("address", form.fields)
        self.assertIn("ghana_card_number", form.fields)
        self.assertIn("digital_address", form.fields)


class GuestListTests(TestCase):
    def setUp(self):
        self.admin_group = Group.objects.create(name="Admin")
        self.user = User.objects.create_user(username="guestadmin", password="pass123456")
        self.user.groups.add(self.admin_group)
        self.client.force_login(self.user)
        Guest.objects.create(
            first_name="Ama",
            last_name="Boateng",
            phone_number="0241000000",
            ghana_card_number="GHA-123456789-0",
        )

    def test_guest_list_shows_ghana_card_number(self):
        response = self.client.get(reverse("guest-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ghana Card Number")
        self.assertContains(response, "GHA-123456789-0")

    def test_guest_list_filters_by_search_query(self):
        Guest.objects.create(
            first_name="Kojo",
            last_name="Mensah",
            phone_number="0242222222",
            ghana_card_number="GHA-999999999-9",
        )

        response = self.client.get(reverse("guest-list"), {"q": "Boateng"})
        self.assertEqual(response.status_code, 200)
        guests = list(response.context["guests"])
        self.assertEqual(len(guests), 1)
        self.assertEqual(guests[0].last_name, "Boateng")
        self.assertContains(response, "Ama Boateng")
        self.assertNotContains(response, "Kojo Mensah")
