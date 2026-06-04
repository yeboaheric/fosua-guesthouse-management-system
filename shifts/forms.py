from django import forms

from accounts.models import Employee, Rota
from shifts.models import ShiftHandover, ShiftHandoverUpdate


class ShiftHandoverForm(forms.ModelForm):
    class Meta:
        model = ShiftHandover
        fields = ["started_at", "ended_at", "summary"]
        widgets = {
            "started_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "ended_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "summary": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        self.fields["started_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["ended_at"].input_formats = ["%Y-%m-%dT%H:%M"]

    def clean(self):
        cleaned_data = super().clean()
        started_at = cleaned_data.get("started_at")
        ended_at = cleaned_data.get("ended_at")
        if started_at and ended_at and ended_at <= started_at:
            raise forms.ValidationError("Shift end time must be after start time.")
        return cleaned_data


class ShiftHandoverUpdateForm(forms.ModelForm):
    class Meta:
        model = ShiftHandoverUpdate
        fields = ["note"]
        widgets = {
            "note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["note"].widget.attrs["class"] = "form-control"


class RosterFilterForm(forms.Form):
    """Form for filtering synced weekly rosters by date range and staff details."""

    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        label="Start date",
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        label="End date",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        departments = sorted(
            {
                department
                for department in Employee.objects.exclude(department="").values_list("department", flat=True)
                if department
            }
        )
        shift_ranges = sorted(
            {
                (
                    f"{rota.opening_time.strftime('%H:%M')}-{rota.closing_time.strftime('%H:%M')}",
                    f"{rota.opening_time.strftime('%H:%M')} - {rota.closing_time.strftime('%H:%M')}",
                )
                for rota in Rota.objects.exclude(opening_time__isnull=True).exclude(closing_time__isnull=True)
            }
        )

        self.fields["department"] = forms.ChoiceField(
            choices=[("", "All departments")] + [(department, department) for department in departments],
            required=False,
            widget=forms.Select(attrs={"class": "form-select"}),
        )
        self.fields["shift"] = forms.ChoiceField(
            choices=[("", "All shifts")] + list(shift_ranges),
            required=False,
            widget=forms.Select(attrs={"class": "form-select"}),
        )
        self.fields["employee"] = forms.ModelChoiceField(
            queryset=Employee.objects.filter(employment_status="active").order_by("last_name", "first_name"),
            required=False,
            widget=forms.Select(attrs={"class": "form-select"}),
        )
        self.fields["role"] = forms.CharField(
            required=False,
            widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Manager, Supervisor"}),
        )
        self.fields["status"] = forms.ChoiceField(
            choices=[("", "All statuses")] + list(Employee.EMPLOYMENT_STATUS_CHOICES),
            required=False,
            widget=forms.Select(attrs={"class": "form-select"}),
        )
