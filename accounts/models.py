from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum

from accounts.permissions import ACCESS_MODULE_CHOICES, ACTION_CHOICES, user_has_permission


class StatusTrackingMixin(models.Model):
    status_history = GenericRelation(
        "accounts.StatusHistory",
        content_type_field="content_type",
        object_id_field="object_id",
        related_query_name="status_history",
    )
    status_field = "status"

    class Meta:
        abstract = True

    def _get_previous_status(self):
        if not self.pk:
            return None
        previous = self.__class__.objects.filter(pk=self.pk).values(self.status_field).first()
        if previous is None:
            return None
        return previous.get(self.status_field)

    def save(self, *args, **kwargs):
        changed_by = kwargs.pop("changed_by", None)
        previous_status = self._get_previous_status()
        result = super().save(*args, **kwargs)
        current_status = getattr(self, self.status_field, None)
        if previous_status is not None and current_status != previous_status:
            from accounts.audit import get_current_user

            history = StatusHistory.objects.create(
                content_type=ContentType.objects.get_for_model(self),
                object_id=self.pk,
                object_repr=str(self),
                previous_status=previous_status or "",
                new_status=current_status or "",
                changed_by=changed_by or get_current_user(),
            )
            Notification.create_from_status_history(history)
        return result


class StatusHistory(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=255)
    content_object = GenericForeignKey("content_type", "object_id")
    object_repr = models.CharField(max_length=255)
    previous_status = models.CharField(max_length=120, blank=True)
    new_status = models.CharField(max_length=120)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="status_history_entries",
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-changed_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["changed_at"]),
        ]

    def __str__(self):
        return f"{self.object_repr}: {self.previous_status} → {self.new_status}"


class Notification(models.Model):
    class Level(models.TextChoices):
        INFO = "info", "Info"
        SUCCESS = "success", "Success"
        WARNING = "warning", "Warning"
        DANGER = "danger", "Danger"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    title = models.CharField(max_length=160)
    message = models.TextField(blank=True)
    link = models.CharField(max_length=255, blank=True)
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.INFO)
    read_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "read_at"])]

    def __str__(self):
        return self.title

    @classmethod
    def create_from_status_history(cls, history):
        title = f"{history.object_repr} status updated"
        message = f"{history.previous_status or 'Unknown'} → {history.new_status}"
        return cls.objects.create(
            title=title,
            message=message,
            link="",
            level=cls.Level.INFO,
            user=history.changed_by,
        )


class Employee(StatusTrackingMixin, models.Model):
    EMPLOYEE_ID_PREFIX = "EMP"
    EMPLOYEE_ID_PADDING = 4

    TITLE_CHOICES = [
        ("mr", "Mr."),
        ("mrs", "Mrs."),
        ("miss", "Miss"),
        ("sir", "Sir"),
    ]

    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    ]

    POSITION_CHOICES = [
        ("hotel_manager", "Hotel Manager"),
        ("cleaner", "Cleaner"),
        ("security", "Security"),
        ("receptionist", "Receptionist"),
    ]

    MARITAL_STATUS_CHOICES = [
        ("single", "Single"),
        ("married", "Married"),
        ("divorced", "Divorced"),
        ("widowed", "Widowed"),
        ("other", "Other"),
    ]

    RELIGION_CHOICES = [
        ("christian", "Christian"),
        ("muslim", "Muslim"),
    ]

    EMPLOYMENT_STATUS_CHOICES = [
        ("active", "Active"),
        ("annual_leave", "Annual Leave"),
        ("sick_leave", "Sick Leave"),
        ("family_emergency", "Family Emergency"),
        ("suspension", "Suspension"),
        ("terminated", "Terminated"),
    ]

    TERMINATION_REASON_CHOICES = [
        ("resignation", "Resignation"),
        ("contract_expired", "Contract Expired"),
        ("retirement", "Retirement"),
        ("dismissal", "Dismissal"),
        ("redundancy", "Redundancy"),
        ("abscondment", "Abscondment"),
        ("mutual_separation", "Mutual Separation"),
        ("death", "Death"),
        ("other", "Other"),
    ]

    employee_id = models.CharField(max_length=60, unique=True, blank=True, null=True)
    title = models.CharField(max_length=10, choices=TITLE_CHOICES, blank=True)
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    date_of_birth = models.DateField()
    nationality = models.CharField(max_length=120)
    ghana_card_number = models.CharField(max_length=100, unique=True)
    ghana_card_expiry_date = models.DateField(blank=True, null=True)
    ssnit_number = models.CharField(max_length=100, blank=True)
    contact_number = models.CharField(max_length=40)
    email = models.EmailField(blank=True)
    residential_address = models.CharField(max_length=255, blank=True)
    department = models.CharField(max_length=120, blank=True)
    job_title = models.CharField(max_length=120, blank=True)
    salary_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    supervisor = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="team_members",
    )
    gps_address = models.CharField(max_length=255, blank=True)
    emergency_contact_name = models.CharField(max_length=255, blank=True)
    next_of_kin = models.CharField(max_length=255, blank=True)
    next_of_kin_contact = models.CharField(max_length=40, blank=True)
    next_of_kin_relationship = models.CharField(max_length=120, blank=True)
    start_date = models.DateField()
    leave_entitlement_days = models.PositiveIntegerField(default=21)
    termination_date = models.DateField(blank=True, null=True)
    termination_reason_choice = models.CharField(max_length=40, choices=TERMINATION_REASON_CHOICES, blank=True)
    termination_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_employee_terminations",
    )
    termination_exit_interview_notes = models.TextField(blank=True)
    company_assets_returned = models.BooleanField(default=False)
    termination_remarks = models.TextField(blank=True)
    termination_reason = models.TextField(blank=True)
    emergency_contact_number = models.CharField(max_length=40, blank=True)
    position = models.CharField(max_length=20, choices=POSITION_CHOICES)
    employment_status = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_STATUS_CHOICES,
        default="active",
    )
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES)
    ethnic_origin = models.CharField(max_length=120, blank=True)
    religion = models.CharField(max_length=20, choices=RELIGION_CHOICES, blank=True)
    passport_photo = models.ImageField(
        upload_to="employee_photos/",
        blank=True,
        null=True,
        help_text="Upload a passport-style photo.",
    )
    status_field = "employment_status"
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Employee"
        verbose_name_plural = "Employees"

    @classmethod
    def _next_employee_id(cls):
        max_number = 0
        employee_ids = (
            cls.objects.select_for_update()
            .exclude(employee_id__isnull=True)
            .exclude(employee_id="")
            .values_list("employee_id", flat=True)
        )
        for employee_id in employee_ids:
            normalized_id = str(employee_id).strip().upper()
            if not normalized_id.startswith(cls.EMPLOYEE_ID_PREFIX):
                continue
            suffix = normalized_id[len(cls.EMPLOYEE_ID_PREFIX):]
            if suffix.isdigit():
                max_number = max(max_number, int(suffix))
        return f"{cls.EMPLOYEE_ID_PREFIX}{max_number + 1:0{cls.EMPLOYEE_ID_PADDING}d}"

    def __str__(self):
        if self.employee_id:
            return f"{self.employee_id} - {self.first_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def annual_leave_taken_days(self):
        return (
            self.leave_requests.filter(
                leave_type="annual",
                approval_status=LeaveRequest.ApprovalStatus.APPROVED,
            ).aggregate(total=Sum("days"))["total"]
            or 0
        )

    @property
    def annual_leave_balance(self):
        return max(self.leave_entitlement_days - int(self.annual_leave_taken_days or 0), 0)

    @property
    def expiring_certifications_count(self):
        from django.utils import timezone

        today = timezone.localdate()
        cutoff = today + timedelta(days=365)
        return self.qualifications.filter(expiry_date__lte=cutoff).count()

    def save(self, *args, **kwargs):
        if self.employee_id:
            self.employee_id = str(self.employee_id).strip().upper()
            return super().save(*args, **kwargs)

        for _ in range(5):
            try:
                with transaction.atomic():
                    self.employee_id = self._next_employee_id()
                    return super().save(*args, **kwargs)
            except IntegrityError as exc:
                if "employee_id" not in str(exc).lower():
                    raise
                self.employee_id = None
        raise IntegrityError("Could not generate a unique sequential employee ID.")


class Rota(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="rota_entries",
    )
    period = models.CharField(max_length=255, blank=True)
    period_start = models.DateField(blank=True, null=True)
    period_end = models.DateField(blank=True, null=True)
    staff_members = models.ManyToManyField(Employee, blank=True, related_name="rotas")
    opening_time = models.TimeField(blank=True, null=True)
    closing_time = models.TimeField(blank=True, null=True)
    shift_rules = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Rota"
        verbose_name_plural = "Rotas"

    def __str__(self):
        if self.employee_id:
            return f"{self.employee} rota"
        if self.period:
            return self.period
        return f"{self.period_start} to {self.period_end}"

    @property
    def operating_hours(self):
        if not self.opening_time or not self.closing_time:
            return "-"
        return f"{self.opening_time.strftime('%I:%M %p')} to {self.closing_time.strftime('%I:%M %p')}"

    @property
    def total_hours(self):
        if not all([self.period_start, self.period_end, self.opening_time, self.closing_time]):
            return 0

        day_count = (self.period_end - self.period_start).days + 1
        opening_minutes = self.opening_time.hour * 60 + self.opening_time.minute
        closing_minutes = self.closing_time.hour * 60 + self.closing_time.minute
        shift_minutes = max(closing_minutes - opening_minutes, 0)
        return round((shift_minutes / 60) * day_count, 2)

    @property
    def daily_hours(self):
        if not self.opening_time or not self.closing_time:
            return 0

        opening_minutes = self.opening_time.hour * 60 + self.opening_time.minute
        closing_minutes = self.closing_time.hour * 60 + self.closing_time.minute
        shift_minutes = max(closing_minutes - opening_minutes, 0)
        return round(shift_minutes / 60, 2)


class EmployeeDocument(models.Model):
    class DocumentType(models.TextChoices):
        NATIONAL_ID = "national_id", "National ID"
        CONTRACT = "contract", "Employment Contract"
        CV = "cv", "CV"
        APPOINTMENT = "appointment_letter", "Appointment Letter"
        CERTIFICATE = "certificate", "Certificate"
        OTHER = "other", "Other"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=40, choices=DocumentType.choices)
    title = models.CharField(max_length=160)
    file = models.FileField(upload_to="employee_documents/")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.employee}"


class EmployeeQualification(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="qualifications")
    qualification_name = models.CharField(max_length=160)
    institution = models.CharField(max_length=160)
    certificate_number = models.CharField(max_length=120, blank=True)
    certification_date = models.DateField()
    expiry_date = models.DateField(blank=True, null=True)
    certificate_copy = models.FileField(upload_to="employee_certifications/", blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-certification_date"]

    def __str__(self):
        return f"{self.qualification_name} - {self.employee}"


class LeaveRequest(models.Model):
    class LeaveType(models.TextChoices):
        ANNUAL = "annual", "Annual Leave"
        SICK = "sick", "Sick Leave"
        FAMILY = "family_emergency", "Family Emergency"
        STUDY = "study", "Study Leave"
        MATERNITY = "maternity", "Maternity Leave"
        UNPAID = "unpaid", "Unpaid Leave"
        OTHER = "other", "Other"

    class ApprovalStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.CharField(max_length=30, choices=LeaveType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.PositiveIntegerField(default=1)
    return_to_work_date = models.DateField()
    reason = models.TextField()
    approval_status = models.CharField(max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING)
    approving_manager = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_leave_requests",
    )
    supporting_document = models.FileField(upload_to="leave_requests/", blank=True, null=True)
    decision_notes = models.TextField(blank=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.employee} {self.get_leave_type_display()}"

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date:
            self.days = max((self.end_date - self.start_date).days + 1, 1)
            if not self.return_to_work_date:
                self.return_to_work_date = self.end_date + timedelta(days=1)
        super().save(*args, **kwargs)


class AttendanceRecord(models.Model):
    class ShiftType(models.TextChoices):
        MORNING = "morning", "Morning"
        AFTERNOON = "afternoon", "Afternoon"
        EVENING = "evening", "Evening"
        OVERNIGHT = "overnight", "Overnight"
        CUSTOM = "custom", "Custom"

    class AttendanceStatus(models.TextChoices):
        PRESENT = "present", "Present"
        LATE = "late", "Late"
        ABSENT = "absent", "Absent"
        ON_LEAVE = "on_leave", "On Leave"
        OFF_DUTY = "off_duty", "Off Duty"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="attendance_records")
    work_date = models.DateField()
    shift_type = models.CharField(max_length=20, choices=ShiftType.choices, default=ShiftType.MORNING)
    check_in = models.DateTimeField(blank=True, null=True)
    check_out = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=AttendanceStatus.choices, default=AttendanceStatus.PRESENT)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-work_date", "employee__last_name"]

    def __str__(self):
        return f"{self.employee} - {self.work_date}"


class PayrollRecord(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="payroll_records")
    pay_period_start = models.DateField()
    pay_period_end = models.DateField()
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    overtime_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    paid_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-pay_period_start"]

    def __str__(self):
        return f"{self.employee} payroll {self.pay_period_start} - {self.pay_period_end}"


class PerformanceReview(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="performance_reviews")
    review_date = models.DateField()
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="employee_reviews")
    rating = models.PositiveSmallIntegerField(default=3)
    summary = models.TextField(blank=True)
    strengths = models.TextField(blank=True)
    improvement_areas = models.TextField(blank=True)
    next_review_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-review_date"]

    def __str__(self):
        return f"{self.employee} review {self.review_date}"


class DisciplinaryRecord(models.Model):
    class RecordType(models.TextChoices):
        WARNING = "warning", "Warning"
        SUSPENSION = "suspension", "Suspension"
        QUERY = "query", "Query"
        FINAL_WARNING = "final_warning", "Final Warning"
        OTHER = "other", "Other"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="disciplinary_records")
    incident_date = models.DateField()
    record_type = models.CharField(max_length=20, choices=RecordType.choices)
    details = models.TextField()
    action_taken = models.TextField(blank=True)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-incident_date"]

    def __str__(self):
        return f"{self.employee} - {self.get_record_type_display()}"


class TrainingRecord(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="training_records")
    training_name = models.CharField(max_length=160)
    provider = models.CharField(max_length=160, blank=True)
    start_date = models.DateField(blank=True, null=True)
    completion_date = models.DateField(blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    certificate_file = models.FileField(upload_to="employee_training/", blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-completion_date", "-created_at"]

    def __str__(self):
        return f"{self.training_name} - {self.employee}"


class EmploymentHistoryEntry(models.Model):
    class ChangeType(models.TextChoices):
        HIRED = "hired", "Hired"
        PROMOTED = "promoted", "Promoted"
        TRANSFERRED = "transferred", "Transferred"
        LEAVE = "leave", "Leave"
        TRAINING = "training", "Training"
        APPRAISAL = "appraisal", "Appraisal"
        TERMINATION = "termination", "Termination"
        OTHER = "other", "Other"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="history_entries")
    change_type = models.CharField(max_length=20, choices=ChangeType.choices)
    effective_date = models.DateField()
    description = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="employee_history_entries")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-effective_date", "-created_at"]

    def __str__(self):
        return f"{self.employee} - {self.get_change_type_display()}"


class UserAccessProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="access_profile",
    )
    dashboard_access = models.BooleanField(default=True)
    reservations_access = models.BooleanField(default=True)
    rooms_access = models.BooleanField(default=True)
    guests_access = models.BooleanField(default=True)
    payments_access = models.BooleanField(default=True)
    services_access = models.BooleanField(default=True)
    housekeeping_access = models.BooleanField(default=True)
    inventory_access = models.BooleanField(default=False)
    pos_access = models.BooleanField(default=True)
    notifications_access = models.BooleanField(default=True)
    analytics_access = models.BooleanField(default=True)
    reports_access = models.BooleanField(default=False)
    settings_access = models.BooleanField(default=False)
    staff_management_access = models.BooleanField(default=False)
    handovers_access = models.BooleanField(default=True)
    users_roles_access = models.BooleanField(default=False)

    class Meta:
        verbose_name = "User Access Profile"
        verbose_name_plural = "User Access Profiles"

    def __str__(self):
        return f"Access profile for {self.user.username}"

    def has_module_access(self, module_name):
        return self.has_permission(module_name, "view")

    def has_permission(self, module_name, action="view"):
        return user_has_permission(self.user, module_name, action)


class StaffProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="staff_profile",
    )
    phone_number = models.CharField(max_length=40, blank=True)
    employee_id = models.CharField(max_length=80, blank=True, unique=True, null=True)
    department = models.CharField(max_length=120, blank=True)
    profile_image = models.ImageField(upload_to="staff_profiles/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return f"Staff profile for {self.user.username}"


class RolePermission(models.Model):
    role = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="role_permissions",
    )
    module = models.CharField(max_length=40, choices=ACCESS_MODULE_CHOICES)
    can_view = models.BooleanField(default=False)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_approve = models.BooleanField(default=False)
    can_export = models.BooleanField(default=False)
    can_print = models.BooleanField(default=False)
    can_manage = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["role__name", "module"]
        constraints = [
            models.UniqueConstraint(fields=["role", "module"], name="unique_role_permission_per_module"),
        ]

    def __str__(self):
        return f"{self.role.name} / {self.get_module_display()}"

    def allows(self, action="view"):
        if self.can_manage:
            return True
        return bool(getattr(self, f"can_{action}", False))


class AuditLog(models.Model):
    class ActionType(models.TextChoices):
        LOGIN = "login", "Login"
        LOGOUT = "logout", "Logout"
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        APPROVE = "approve", "Approve"
        PERMISSION_CHANGE = "permission_change", "Permission Change"
        EXPORT = "export", "Export"
        PRINT = "print", "Print"
        MANAGE = "manage", "Manage"
        OTHER = "other", "Other"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=40, choices=ActionType.choices)
    module = models.CharField(max_length=40, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    object_id = models.CharField(max_length=120, blank=True)
    path = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    status_code = models.PositiveSmallIntegerField(blank=True, null=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["module", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_action_display()} by {self.user or 'system'}"
