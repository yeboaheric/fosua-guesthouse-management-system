from django import forms

from rooms.models import Room
from django.contrib.auth import get_user_model
from .models import HousekeepingTask, HousekeepingHistory, InspectionRecord
User = get_user_model()


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ["room_number", "room_type", "status", "base_rate", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = (
                "form-select"
                if isinstance(field.widget, forms.Select)
                else "form-control"
            )
            field.widget.attrs["class"] = css_class


class HousekeepingStatusForm(forms.Form):
    room = forms.ModelChoiceField(queryset=Room.objects.order_by("room_number"), widget=forms.Select(attrs={"class": "form-select"}))
    new_status = forms.ChoiceField(choices=Room.HousekeepingStatus.choices, widget=forms.Select(attrs={"class": "form-select"}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}))


class HousekeepingTaskForm(forms.ModelForm):
    class Meta:
        model = HousekeepingTask
        fields = ["room", "title", "description", "assigned_to", "due_date"]
        widgets = {
            "room": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "assigned_to": forms.Select(attrs={"class": "form-select"}),
            "due_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }


class InspectionForm(forms.ModelForm):
    class Meta:
        model = InspectionRecord
        fields = ["room", "inspector", "passed", "notes"]
        widgets = {
            "room": forms.Select(attrs={"class": "form-select"}),
            "inspector": forms.Select(attrs={"class": "form-select"}),
            "passed": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class HousekeepingTaskToiletryForm(forms.ModelForm):
    class Meta:
        model = __import__("rooms.models", fromlist=["HousekeepingTaskToiletry"]).HousekeepingTaskToiletry
        fields = ["item", "quantity"]
        widgets = {
            "item": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}),
        }
