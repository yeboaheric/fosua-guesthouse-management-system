from datetime import date

from django import forms

from accounts.models import Employee


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
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "termination_date": forms.DateInput(attrs={"type": "date"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "contact_number": forms.TextInput(attrs={"autocomplete": "tel"}),
            "emergency_contact_number": forms.TextInput(attrs={"autocomplete": "tel"}),
            "gps_address": forms.Textarea(attrs={"rows": 2}),
        }
