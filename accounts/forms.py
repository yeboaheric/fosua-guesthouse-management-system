from datetime import date

from django import forms
from django.core.validators import RegexValidator

from accounts.models import Employee, Rota


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
            "first_name",
            "last_name",
            "date_of_birth",
            "nationality",
            "ghana_card_number",
            "contact_number",
            "email",
            "gps_address",
            "next_of_kin",
            "start_date",
            "termination_date",
            "emergency_contact_number",
            "position",
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
            "email": forms.EmailInput(attrs={"autocomplete": "email", "class": "form-control"}),
            "contact_number": forms.TextInput(attrs={"autocomplete": "tel", "class": "form-control"}),
            "emergency_contact_number": forms.TextInput(attrs={"autocomplete": "tel", "class": "form-control"}),
            "ghana_card_number": forms.TextInput(attrs={"placeholder": "GHA-123456789-0", "class": "form-control"}),
            "gps_address": forms.TextInput(attrs={"placeholder": "AK-1234-56", "class": "form-control"}),
            "nationality": forms.TextInput(attrs={"class": "form-control"}),
            "next_of_kin": forms.TextInput(attrs={"class": "form-control"}),
            "passport_photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "position": forms.Select(attrs={"class": "form-select"}),
            "gender": forms.Select(attrs={"class": "form-select"}),
            "marital_status": forms.Select(attrs={"class": "form-select"}),
            "religion": forms.Select(attrs={"class": "form-select"}),
            "ethnic_origin": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
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
            "period",
            "period_start",
            "period_end",
            "staff_members",
            "opening_time",
            "closing_time",
            "shift_rules",
        ]
        widgets = {
            "period_start": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "period_end": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "opening_time": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "closing_time": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "staff_members": forms.SelectMultiple(attrs={"class": "form-select"}),
            "shift_rules": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "period": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["period_start"].required = True
        self.fields["period_end"].required = True
        self.fields["opening_time"].required = True
        self.fields["closing_time"].required = True
        self.fields["staff_members"].required = False
