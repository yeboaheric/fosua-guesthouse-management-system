from django import forms
from django.contrib.auth.models import Group, User
from django.core.validators import RegexValidator

from accounts.models import (
    AttendanceRecord,
    DisciplinaryRecord,
    Employee,
    EmployeeDocument,
    EmployeeQualification,
    EmploymentHistoryEntry,
    LeaveRequest,
    PayrollRecord,
    PerformanceReview,
    Rota,
    RolePermission,
    StaffProfile,
    TrainingRecord,
    UserAccessProfile,
)
from accounts.permissions import (
    ACTION_CHOICES,
    ACCESS_MODULE_CHOICES,
    access_defaults_for_roles,
    default_permissions_for_role,
)


GHA_CARD_VALIDATOR = RegexValidator(
    regex=r"^GHA-\d{9}-\d$",
    message="Enter a valid Ghana Card number in the format GHA-123456789-0.",
)

GPS_ADDRESS_VALIDATOR = RegexValidator(
    regex=r"^[A-Z]{2}-[A-Z0-9]{4}-[A-Z0-9]{2}$",
    message="Enter a valid GPS address in the format AK-1234-56.",
)


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            "employee_id",
            "title",
            "first_name",
            "last_name",
            "date_of_birth",
            "nationality",
            "ghana_card_number",
            "ghana_card_expiry_date",
            "ssnit_number",
            "contact_number",
            "email",
            "residential_address",
            "department",
            "job_title",
            "salary_amount",
            "supervisor",
            "gps_address",
            "emergency_contact_name",
            "next_of_kin",
            "next_of_kin_contact",
            "next_of_kin_relationship",
            "start_date",
            "leave_entitlement_days",
            "termination_date",
            "termination_reason_choice",
            "termination_approved_by",
            "termination_exit_interview_notes",
            "company_assets_returned",
            "termination_remarks",
            "termination_reason",
            "emergency_contact_number",
            "position",
            "employment_status",
            "gender",
            "marital_status",
            "ethnic_origin",
            "religion",
            "passport_photo",
        ]
        widgets = {
            "employee_id": forms.TextInput(attrs={"class": "form-control"}),
            "date_of_birth": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "termination_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "ghana_card_expiry_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email", "class": "form-control"}),
            "contact_number": forms.TextInput(attrs={"autocomplete": "tel", "class": "form-control"}),
            "emergency_contact_number": forms.TextInput(attrs={"autocomplete": "tel", "class": "form-control"}),
            "ghana_card_number": forms.TextInput(attrs={"placeholder": "GHA-123456789-0", "class": "form-control"}),
            "gps_address": forms.TextInput(attrs={"placeholder": "AK-1234-56", "class": "form-control"}),
            "nationality": forms.TextInput(attrs={"class": "form-control"}),
            "next_of_kin": forms.TextInput(attrs={"class": "form-control"}),
            "next_of_kin_contact": forms.TextInput(attrs={"class": "form-control"}),
            "next_of_kin_relationship": forms.TextInput(attrs={"class": "form-control"}),
            "ssnit_number": forms.TextInput(attrs={"class": "form-control"}),
            "passport_photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "title": forms.Select(attrs={"class": "form-select"}),
            "position": forms.Select(attrs={"class": "form-select"}),
            "employment_status": forms.Select(attrs={"class": "form-select"}),
            "termination_reason_choice": forms.Select(attrs={"class": "form-select"}),
            "termination_approved_by": forms.Select(attrs={"class": "form-select"}),
            "gender": forms.Select(attrs={"class": "form-select"}),
            "marital_status": forms.Select(attrs={"class": "form-select"}),
            "religion": forms.Select(attrs={"class": "form-select"}),
            "ethnic_origin": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "residential_address": forms.TextInput(attrs={"class": "form-control"}),
            "department": forms.TextInput(attrs={"class": "form-control"}),
            "job_title": forms.TextInput(attrs={"class": "form-control"}),
            "salary_amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "supervisor": forms.Select(attrs={"class": "form-select"}),
            "emergency_contact_name": forms.TextInput(attrs={"class": "form-control"}),
            "leave_entitlement_days": forms.NumberInput(attrs={"class": "form-control"}),
            "termination_reason": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "termination_exit_interview_notes": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "termination_remarks": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "company_assets_returned": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        supervisor_queryset = Employee.objects.order_by("last_name", "first_name")
        if self.instance and self.instance.pk:
            supervisor_queryset = supervisor_queryset.exclude(pk=self.instance.pk)
        self.fields["supervisor"].queryset = supervisor_queryset
        self.fields["termination_approved_by"].queryset = User.objects.order_by("username")
        for field_name in self.fields:
            field = self.fields[field_name]
            if field.widget.attrs.get("class") is None:
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs["class"] = "form-select"
                else:
                    field.widget.attrs["class"] = "form-control"

    def clean_ghana_card_number(self):
        value = self.cleaned_data.get("ghana_card_number", "").strip().upper()
        GHA_CARD_VALIDATOR(value)
        return value

    def clean_gps_address(self):
        value = self.cleaned_data.get("gps_address", "").strip().upper()
        if not value:
            return ""
        GPS_ADDRESS_VALIDATOR(value)
        return value


class EmployeeQualificationForm(forms.ModelForm):
    class Meta:
        model = EmployeeQualification
        fields = [
            "qualification_name",
            "institution",
            "certificate_number",
            "certification_date",
            "expiry_date",
            "certificate_copy",
            "notes",
        ]
        widgets = {
            "qualification_name": forms.TextInput(attrs={"class": "form-control"}),
            "institution": forms.TextInput(attrs={"class": "form-control"}),
            "certificate_number": forms.TextInput(attrs={"class": "form-control"}),
            "certification_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "expiry_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "certificate_copy": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }


class EmployeeDocumentForm(forms.ModelForm):
    class Meta:
        model = EmployeeDocument
        fields = ["document_type", "title", "file", "description"]
        widgets = {
            "document_type": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = [
            "leave_type",
            "start_date",
            "end_date",
            "days",
            "return_to_work_date",
            "reason",
            "approval_status",
            "approving_manager",
            "supporting_document",
            "decision_notes",
        ]
        widgets = {
            "leave_type": forms.Select(attrs={"class": "form-select"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "days": forms.NumberInput(attrs={"class": "form-control"}),
            "return_to_work_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "reason": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "approval_status": forms.Select(attrs={"class": "form-select"}),
            "approving_manager": forms.Select(attrs={"class": "form-select"}),
            "supporting_document": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "decision_notes": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["approving_manager"].queryset = User.objects.order_by("username")


class AttendanceRecordForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        fields = ["work_date", "shift_type", "check_in", "check_out", "status", "notes"]
        widgets = {
            "work_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "shift_type": forms.Select(attrs={"class": "form-select"}),
            "check_in": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
            "check_out": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }


class PayrollRecordForm(forms.ModelForm):
    class Meta:
        model = PayrollRecord
        fields = [
            "pay_period_start",
            "pay_period_end",
            "basic_salary",
            "allowances",
            "deductions",
            "overtime_pay",
            "net_pay",
            "payment_status",
            "paid_at",
            "notes",
        ]
        widgets = {
            "pay_period_start": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "pay_period_end": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "basic_salary": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "allowances": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "deductions": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "overtime_pay": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "net_pay": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "payment_status": forms.Select(attrs={"class": "form-select"}),
            "paid_at": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
            "notes": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }


class PerformanceReviewForm(forms.ModelForm):
    class Meta:
        model = PerformanceReview
        fields = [
            "review_date",
            "reviewer",
            "rating",
            "summary",
            "strengths",
            "improvement_areas",
            "next_review_date",
        ]
        widgets = {
            "review_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "reviewer": forms.Select(attrs={"class": "form-select"}),
            "rating": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 5}),
            "summary": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "strengths": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "improvement_areas": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "next_review_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reviewer"].queryset = User.objects.order_by("username")


class DisciplinaryRecordForm(forms.ModelForm):
    class Meta:
        model = DisciplinaryRecord
        fields = ["incident_date", "record_type", "details", "action_taken", "resolved", "resolved_at", "notes"]
        widgets = {
            "incident_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "record_type": forms.Select(attrs={"class": "form-select"}),
            "details": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "action_taken": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "resolved": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "resolved_at": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
            "notes": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }


class TrainingRecordForm(forms.ModelForm):
    class Meta:
        model = TrainingRecord
        fields = ["training_name", "provider", "start_date", "completion_date", "expiry_date", "certificate_file", "notes"]
        widgets = {
            "training_name": forms.TextInput(attrs={"class": "form-control"}),
            "provider": forms.TextInput(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "completion_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "expiry_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "certificate_file": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }


class EmploymentHistoryForm(forms.ModelForm):
    class Meta:
        model = EmploymentHistoryEntry
        fields = ["change_type", "effective_date", "description"]
        widgets = {
            "change_type": forms.Select(attrs={"class": "form-select"}),
            "effective_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }


class RotaForm(forms.ModelForm):
    class Meta:
        model = Rota
        fields = [
            "employee",
            "period",
            "period_start",
            "period_end",
            "opening_time",
            "closing_time",
            "shift_rules",
        ]
        widgets = {
            "period_start": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "period_end": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "opening_time": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "closing_time": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "employee": forms.Select(attrs={"class": "form-select"}),
            "shift_rules": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "period": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["period_start"].required = True
        self.fields["period_end"].required = True
        self.fields["opening_time"].required = True
        self.fields["closing_time"].required = True
        self.fields["employee"].required = True
        self.fields["employee"].queryset = Employee.objects.filter(
            employment_status="active"
        ).order_by("last_name", "first_name")

    def clean(self):
        cleaned_data = super().clean()
        period_start = cleaned_data.get("period_start")
        period_end = cleaned_data.get("period_end")
        opening_time = cleaned_data.get("opening_time")
        closing_time = cleaned_data.get("closing_time")

        if period_start and period_end and period_end < period_start:
            raise forms.ValidationError("Roster end date must be on or after the start date.")

        if opening_time and closing_time and closing_time <= opening_time:
            raise forms.ValidationError("Shift end time must be after the start time.")

        return cleaned_data


class StaffUserForm(forms.Form):
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)
    phone_number = forms.CharField(max_length=40, required=False)
    employee_id = forms.CharField(max_length=80, required=False)
    department = forms.CharField(max_length=120, required=False)
    profile_image = forms.ImageField(required=False)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password")
    roles = forms.MultipleChoiceField(
        choices=[],
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )
    is_active = forms.BooleanField(required=False, initial=True)
    is_staff = forms.BooleanField(required=False, initial=True)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["roles"].choices = [(group.name, group.name) for group in Group.objects.order_by("name")]

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            password=self.cleaned_data["password1"],
            email=self.cleaned_data.get("email", ""),
            first_name=self.cleaned_data.get("first_name", ""),
            last_name=self.cleaned_data.get("last_name", ""),
            is_active=self.cleaned_data.get("is_active", True),
            is_staff=self.cleaned_data.get("is_staff", True),
        )
        roles = Group.objects.filter(name__in=self.cleaned_data["roles"])
        user.groups.set(roles)
        UserAccessProfile.objects.create(user=user, **access_defaults_for_roles(self.cleaned_data["roles"]))
        StaffProfile.objects.update_or_create(
            user=user,
            defaults={
                "phone_number": self.cleaned_data.get("phone_number", ""),
                "employee_id": self.cleaned_data.get("employee_id", "") or None,
                "department": self.cleaned_data.get("department", ""),
                "profile_image": self.cleaned_data.get("profile_image"),
            },
        )
        return user


class RoleCreateForm(forms.Form):
    name = forms.CharField(max_length=150)

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if Group.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError("This role already exists.")
        return name

    def save(self):
        name = self.cleaned_data["name"].strip()
        role = Group.objects.create(name=name)
        preset_permissions = default_permissions_for_role(name)
        for module_name, actions in preset_permissions.items():
            values = {
                "can_view": "view" in actions,
                "can_create": "create" in actions,
                "can_edit": "edit" in actions,
                "can_delete": "delete" in actions,
                "can_approve": "approve" in actions,
                "can_export": "export" in actions,
                "can_print": "print" in actions,
                "can_manage": "manage" in actions,
            }
            RolePermission.objects.update_or_create(role=role, module=module_name, defaults=values)
        return role


class RolePermissionForm(forms.Form):
    role_id = forms.IntegerField(widget=forms.HiddenInput)
    role_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-control"}))

    def __init__(self, *args, role=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = role
        self.fields["role_name"].widget.attrs.setdefault("class", "form-control")
        for module_name, module_label in ACCESS_MODULE_CHOICES:
            for action_name, action_label in ACTION_CHOICES:
                field_name = f"{module_name}_{action_name}"
                self.fields[field_name] = forms.BooleanField(required=False, label=f"{module_label} {action_label}")
                self.fields[field_name].widget.attrs["class"] = "form-check-input"

        if role is not None and not self.is_bound:
            self.fields["role_id"].initial = role.pk
            self.fields["role_name"].initial = role.name
            permission_map = {
                perm.module: perm for perm in role.role_permissions.all()
            }
            preset_permissions = default_permissions_for_role(role.name)
            for module_name, _ in ACCESS_MODULE_CHOICES:
                permission = permission_map.get(module_name)
                if permission is None:
                    preset_actions = preset_permissions.get(module_name, set())
                    self.fields[f"{module_name}_view"].initial = "view" in preset_actions
                    self.fields[f"{module_name}_create"].initial = "create" in preset_actions
                    self.fields[f"{module_name}_edit"].initial = "edit" in preset_actions
                    self.fields[f"{module_name}_delete"].initial = "delete" in preset_actions
                    self.fields[f"{module_name}_approve"].initial = "approve" in preset_actions
                    self.fields[f"{module_name}_export"].initial = "export" in preset_actions
                    self.fields[f"{module_name}_print"].initial = "print" in preset_actions
                    self.fields[f"{module_name}_manage"].initial = "manage" in preset_actions
                    continue
                self.fields[f"{module_name}_view"].initial = permission.can_view
                self.fields[f"{module_name}_create"].initial = permission.can_create
                self.fields[f"{module_name}_edit"].initial = permission.can_edit
                self.fields[f"{module_name}_delete"].initial = permission.can_delete
                self.fields[f"{module_name}_approve"].initial = permission.can_approve
                self.fields[f"{module_name}_export"].initial = permission.can_export
                self.fields[f"{module_name}_print"].initial = permission.can_print
                self.fields[f"{module_name}_manage"].initial = permission.can_manage
                if permission.can_manage:
                    for action_name, _ in ACTION_CHOICES:
                        self.fields[f"{module_name}_{action_name}"].initial = True

    def clean_role_id(self):
        role_id = self.cleaned_data["role_id"]
        try:
            self.role = Group.objects.get(pk=role_id)
        except Group.DoesNotExist as exc:
            raise forms.ValidationError("Selected role does not exist.") from exc
        return role_id

    def save(self):
        self.role.name = self.cleaned_data["role_name"].strip()
        self.role.save(update_fields=["name"])

        for module_name, _ in ACCESS_MODULE_CHOICES:
            values = {action_name: self.cleaned_data.get(f"{module_name}_{action_name}", False) for action_name, _ in ACTION_CHOICES}
            if values["manage"]:
                values = {action_name: True for action_name, _ in ACTION_CHOICES}
            elif values["view"]:
                pass
            else:
                values = {action_name: False for action_name, _ in ACTION_CHOICES}

            if any(values.values()):
                RolePermission.objects.update_or_create(
                    role=self.role,
                    module=module_name,
                    defaults={
                        "can_view": values["view"],
                        "can_create": values["create"],
                        "can_edit": values["edit"],
                        "can_delete": values["delete"],
                        "can_approve": values["approve"],
                        "can_export": values["export"],
                        "can_print": values["print"],
                        "can_manage": values["manage"],
                    },
                )
            else:
                RolePermission.objects.filter(role=self.role, module=module_name).delete()

        return self.role


class StaffRoleForm(forms.Form):
    user_id = forms.IntegerField(widget=forms.HiddenInput)
    roles = forms.MultipleChoiceField(
        choices=[],
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)
    is_active = forms.BooleanField(required=False)
    is_staff = forms.BooleanField(required=False)
    phone_number = forms.CharField(max_length=40, required=False)
    employee_id = forms.CharField(max_length=80, required=False)
    department = forms.CharField(max_length=120, required=False)
    profile_image = forms.ImageField(required=False)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["roles"].choices = [(group.name, group.name) for group in Group.objects.order_by("name")]
        if user is not None and not self.is_bound:
            self.fields["roles"].initial = list(user.groups.values_list("name", flat=True))
            self.fields["first_name"].initial = user.first_name
            self.fields["last_name"].initial = user.last_name
            self.fields["email"].initial = user.email
            self.fields["is_active"].initial = user.is_active
            self.fields["is_staff"].initial = user.is_staff
            staff_profile = getattr(user, "staff_profile", None)
            if staff_profile:
                self.fields["phone_number"].initial = staff_profile.phone_number
                self.fields["employee_id"].initial = staff_profile.employee_id
                self.fields["department"].initial = staff_profile.department
                self.fields["profile_image"].initial = staff_profile.profile_image
        for field_name in ["is_active", "is_staff"]:
            self.fields[field_name].widget.attrs.setdefault("class", "form-check-input")

    def clean_user_id(self):
        user_id = self.cleaned_data["user_id"]
        try:
            self.user = User.objects.get(pk=user_id)
        except User.DoesNotExist as exc:
            raise forms.ValidationError("Selected user does not exist.") from exc
        return user_id

    def save(self):
        roles = Group.objects.filter(name__in=self.cleaned_data.get("roles", []))
        self.user.groups.set(roles)
        self.user.first_name = self.cleaned_data.get("first_name", "")
        self.user.last_name = self.cleaned_data.get("last_name", "")
        self.user.email = self.cleaned_data.get("email", "")
        self.user.is_active = self.cleaned_data.get("is_active", False)
        self.user.is_staff = self.cleaned_data.get("is_staff", False)
        self.user.save(update_fields=["first_name", "last_name", "email", "is_active", "is_staff"])

        profile, _ = UserAccessProfile.objects.get_or_create(
            user=self.user,
            defaults=access_defaults_for_roles(self.cleaned_data.get("roles", [])),
        )
        for field_name, value in access_defaults_for_roles(self.cleaned_data.get("roles", [])).items():
            setattr(profile, field_name, value)
        profile.save()
        existing_profile = getattr(self.user, "staff_profile", None)
        profile_image = self.cleaned_data.get("profile_image") or getattr(existing_profile, "profile_image", None)
        StaffProfile.objects.update_or_create(
            user=self.user,
            defaults={
                "phone_number": self.cleaned_data.get("phone_number", ""),
                "employee_id": self.cleaned_data.get("employee_id", "") or None,
                "department": self.cleaned_data.get("department", ""),
                "profile_image": profile_image,
            },
        )
        return self.user
