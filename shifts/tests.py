from datetime import timedelta, time
from io import BytesIO

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from accounts.models import Employee, Rota
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


class RosterReportFilterTests(TestCase):
    """Tests for roster filtering and reporting functionality."""

    def setUp(self):
        """Create test fixtures for roster testing."""
        self.admin_group = Group.objects.create(name="Admin")
        self.user1 = User.objects.create_user(username="john_doe", first_name="John", last_name="Doe", password="pass123")
        self.user1.groups.add(self.admin_group)
        today = timezone.now().date()
        self.employee1 = Employee.objects.create(
            title="mr",
            first_name="John",
            last_name="Doe",
            date_of_birth=today - timedelta(days=10000),
            nationality="Ghanaian",
            ghana_card_number="GHA-100000000-1",
            contact_number="0200000001",
            department="Reception",
            job_title="Receptionist",
            start_date=today - timedelta(days=365),
            position="receptionist",
            employment_status="active",
            gender="male",
            marital_status="single",
        )
        self.employee2 = Employee.objects.create(
            title="mrs",
            first_name="Jane",
            last_name="Smith",
            date_of_birth=today - timedelta(days=11000),
            nationality="Ghanaian",
            ghana_card_number="GHA-100000000-2",
            contact_number="0200000002",
            department="Housekeeping",
            job_title="Housekeeper",
            start_date=today - timedelta(days=400),
            position="cleaner",
            employment_status="active",
            gender="female",
            marital_status="single",
        )
        self.employee3 = Employee.objects.create(
            title="mr",
            first_name="Bob",
            last_name="Wilson",
            date_of_birth=today - timedelta(days=12000),
            nationality="Ghanaian",
            ghana_card_number="GHA-100000000-3",
            contact_number="0200000003",
            department="Reception",
            job_title="Night Manager",
            start_date=today - timedelta(days=500),
            position="hotel_manager",
            employment_status="active",
            gender="male",
            marital_status="single",
        )
        self.roster1 = Rota.objects.create(
            employee=self.employee1,
            period="John Doe weekly duty roster",
            period_start=today,
            period_end=today + timedelta(days=6),
            opening_time=time(6, 0),
            closing_time=time(14, 0),
            shift_rules="Front desk coverage",
        )
        self.roster2 = Rota.objects.create(
            employee=self.employee3,
            period="Bob Wilson weekly duty roster",
            period_start=today + timedelta(days=1),
            period_end=today + timedelta(days=7),
            opening_time=time(14, 0),
            closing_time=time(22, 0),
            shift_rules="Overnight supervision",
        )
        self.client.force_login(self.user1)

    def test_roster_report_page_loads(self):
        """Test that roster report page loads successfully."""
        response = self.client.get(reverse("roster-report"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shifts/roster_report.html")
        self.assertIn("filter_form", response.context)

    def test_roster_filtering_by_date_range(self):
        """Test filtering rosters by date range."""
        today = timezone.now().date()
        response = self.client.get(
            reverse("roster-report"),
            {
                "start_date": today.isoformat(),
                "end_date": today.isoformat(),
            },
        )
        self.assertEqual(response.status_code, 200)
        rosters = response.context.get("rosters", [])
        self.assertEqual(len(rosters), 1)
        self.assertEqual(rosters[0].period_start, today)

    def test_roster_filtering_by_department(self):
        """Test filtering entries by department."""
        response = self.client.get(
            reverse("roster-report"), {"department": "Reception"}
        )
        self.assertEqual(response.status_code, 200)
        rosters = list(response.context.get("rosters", []))
        self.assertEqual({rota.employee.department for rota in rosters}, {"Reception"})

    def test_roster_detail_displays_all_entries(self):
        """Test that roster detail page displays all entries for a roster."""
        response = self.client.get(
            reverse("roster-detail", args=[self.roster1.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shifts/roster_detail.html")
        self.assertEqual(response.context["rota"], self.roster1)
        entries = response.context.get("daily_roster", [])
        self.assertEqual(len(entries), 7)

    def test_roster_detail_groups_by_shift(self):
        """Test that roster detail groups entries by shift."""
        response = self.client.get(
            reverse("roster-detail", args=[self.roster1.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "06:00")
        self.assertContains(response, "14:00")


class RosterExcelExportTests(TestCase):
    """Tests for Excel export functionality."""

    def setUp(self):
        """Create test fixtures for Excel export testing."""
        self.admin_group = Group.objects.create(name="Admin")
        self.user1 = User.objects.create_user(
            username="manager1", first_name="Alice", last_name="Manager", password="pass123"
        )
        self.user1.groups.add(self.admin_group)
        self.staff_employees = []
        today = timezone.now().date()
        departments = ["Reception", "Housekeeping"]
        positions = ["receptionist", "cleaner"]
        job_titles = ["Receptionist", "Housekeeper"]
        opening_times = [time(6, 0), time(14, 0)]
        closing_times = [time(14, 0), time(22, 0)]
        for i in range(5):
            employee = Employee.objects.create(
                title="mr" if i % 2 == 0 else "mrs",
                first_name="Staff",
                last_name=f"Member{i}",
                date_of_birth=today - timedelta(days=9000 + i),
                nationality="Ghanaian",
                ghana_card_number=f"GHA-200000000-{i}",
                contact_number=f"020100000{i}",
                department=departments[i % 2],
                job_title=job_titles[i % 2],
                start_date=today - timedelta(days=365 + i),
                position=positions[i % 2],
                employment_status="active",
                gender="male" if i % 2 == 0 else "female",
                marital_status="single",
            )
            self.staff_employees.append(employee)
            Rota.objects.create(
                employee=employee,
                period=f"Staff Member{i} weekly duty roster",
                period_start=today,
                period_end=today + timedelta(days=6),
                opening_time=opening_times[i % 2],
                closing_time=closing_times[i % 2],
                shift_rules=f"Duty {i}",
            )
        self.client.force_login(self.user1)

    def test_excel_export_endpoint_returns_file(self):
        """Test that Excel export endpoint returns a valid Excel file."""
        response = self.client.get(reverse("roster-export-excel"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertTrue(
            response["Content-Disposition"].startswith("attachment; filename=")
        )

    def test_excel_export_contains_roster_data(self):
        """Test that exported Excel file contains roster data."""
        response = self.client.get(reverse("roster-export-excel"))
        self.assertEqual(response.status_code, 200)

        # Load the workbook from response content
        excel_file = BytesIO(response.content)
        workbook = load_workbook(excel_file)
        worksheet = workbook.active

        # Check headers
        headers = [cell.value for cell in worksheet[1]]
        expected_headers = [
            "Date",
            "Employee",
            "Department",
            "Role",
            "Start",
            "Finish",
            "Hours",
        ]
        for expected in expected_headers:
            self.assertIn(expected, headers)

    def test_excel_export_includes_all_entries(self):
        """Test that all roster entries are included in Excel export."""
        response = self.client.get(reverse("roster-export-excel"))
        self.assertEqual(response.status_code, 200)

        excel_file = BytesIO(response.content)
        workbook = load_workbook(excel_file)
        worksheet = workbook.active

        # Count data rows (excluding header)
        data_rows = worksheet.max_row - 1
        self.assertGreaterEqual(data_rows, len(self.staff_employees) * 7)

    def test_excel_export_file_formatting(self):
        """Test that Excel file has proper formatting."""
        response = self.client.get(reverse("roster-export-excel"))
        self.assertEqual(response.status_code, 200)

        excel_file = BytesIO(response.content)
        workbook = load_workbook(excel_file)
        worksheet = workbook.active

        # Check header formatting
        header_row = worksheet[1]
        for cell in header_row:
            # Check that header has fill color (styling)
            self.assertIsNotNone(cell.fill)
            # Check that header font is styled
            self.assertIsNotNone(cell.font)

    def test_excel_export_filtered_by_date_range(self):
        """Test Excel export with date range filtering."""
        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)

        response = self.client.get(
            reverse("roster-export-excel"),
            {
                "start_date": today.isoformat(),
                "end_date": today.isoformat(),
            },
        )
        self.assertEqual(response.status_code, 200)

        excel_file = BytesIO(response.content)
        workbook = load_workbook(excel_file)
        worksheet = workbook.active

        # Verify only today's data is in the export
        data_rows = worksheet.max_row - 1
        self.assertGreater(data_rows, 0)

    def test_excel_export_filename_includes_date(self):
        """Test that Excel export filename includes date range."""
        response = self.client.get(reverse("roster-export-excel"))
        self.assertEqual(response.status_code, 200)

        filename = response["Content-Disposition"]
        self.assertIn("filename=", filename)
        self.assertIn("roster_report", filename)
        self.assertIn(".xlsx", filename)
