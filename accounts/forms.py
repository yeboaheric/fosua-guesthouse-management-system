from django import forms
from django.contrib.auth.models import Group, User
from django.core.validators import RegexValidator

from accounts.models import Employee, Rota, UserAccessProfile


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
            "gps_address",
            "next_of_kin",
            "next_of_kin_contact",
            "next_of_kin_relationship",
            "start_date",
            "termination_date",
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
            "gender": forms.Select(attrs={"class": "form-select"}),
            "marital_status": forms.Select(attrs={"class": "form-select"}),
            "religion": forms.Select(attrs={"class": "form-select"}),
            "ethnic_origin": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "termination_reason": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        GPS_ADDRESS_VALIDATOR(value)
        return value


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


ROLE_CHOICES = [
    ("Admin", "Admin"),
    ("Receptionist", "Receptionist"),
]

ACCESS_MODULES = [
    ("dashboard_access", "Dashboard"),
    ("reservations_access", "Reservations"),
    ("rooms_access", "Rooms"),
    ("guests_access", "Guests"),
    ("payments_access", "Payments"),
    ("services_access", "Services"),
    ("housekeeping_access", "Housekeeping"),
    ("notifications_access", "Notifications"),
    ("analytics_access", "Analytics"),
    ("reports_access", "Reports"),
    ("settings_access", "Settings"),
    ("staff_management_access", "Staff Management"),
    ("handovers_access", "Shift Handovers"),
    ("users_roles_access", "Users & Roles"),
]

RECEPTION_DEFAULT_ACCESS = {
    "dashboard_access": True,
    "reservations_access": True,
    "rooms_access": True,
    "guests_access": True,
    "payments_access": True,
    "services_access": True,
    "housekeeping_access": True,
    "notifications_access": True,
    "analytics_access": True,
    "reports_access": False,
    "settings_access": False,
    "staff_management_access": False,
    "handovers_access": True,
    "users_roles_access": False,
}

ADMIN_DEFAULT_ACCESS = {field_name: True for field_name, _ in ACCESS_MODULES}


class StaffUserForm(forms.Form):
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password")
    roles = forms.MultipleChoiceField(
        choices=ROLE_CHOICES,
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
        access_defaults = ADMIN_DEFAULT_ACCESS if "Admin" in self.cleaned_data["roles"] else RECEPTION_DEFAULT_ACCESS
        UserAccessProfile.objects.create(user=user, **access_defaults)
        return user


class StaffRoleForm(forms.Form):
    user_id = forms.IntegerField(widget=forms.HiddenInput)
    roles = forms.MultipleChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    is_active = forms.BooleanField(required=False)
    is_staff = forms.BooleanField(required=False)
    access_fields = [field_name for field_name, _ in ACCESS_MODULES]

    for field_name, label in ACCESS_MODULES:
        locals()[field_name] = forms.BooleanField(required=False, label=label)
    del field_name, label

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user is not None and not self.is_bound:
            self.fields["roles"].initial = list(user.groups.values_list("name", flat=True))
            self.fields["is_active"].initial = user.is_active
            self.fields["is_staff"].initial = user.is_staff
            profile = getattr(user, "access_profile", None)
            if profile is None:
                defaults = ADMIN_DEFAULT_ACCESS if user.groups.filter(name="Admin").exists() else RECEPTION_DEFAULT_ACCESS
                profile, _ = UserAccessProfile.objects.get_or_create(user=user, defaults=defaults)
            for field_name, _ in ACCESS_MODULES:
                self.fields[field_name].initial = getattr(profile, field_name)
        for field_name in ["is_active", "is_staff", *self.access_fields]:
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
        self.user.is_active = self.cleaned_data.get("is_active", False)
        self.user.is_staff = self.cleaned_data.get("is_staff", False)
        self.user.save(update_fields=["is_active", "is_staff"])

        profile, _ = UserAccessProfile.objects.get_or_create(user=self.user)
        for field_name, _ in ACCESS_MODULES:
            setattr(profile, field_name, self.cleaned_data.get(field_name, False))
        if "Admin" in self.cleaned_data.get("roles", []):
            for field_name, _ in ACCESS_MODULES:
                setattr(profile, field_name, True)
        profile.save()
        return self.user
