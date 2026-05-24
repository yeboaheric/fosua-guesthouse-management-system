from django import forms

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
