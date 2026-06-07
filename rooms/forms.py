from django import forms
from django.utils import timezone

from rooms.models import HousekeepingItemLog, Room


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


class HousekeepingItemLogForm(forms.ModelForm):
    class Meta:
        model = HousekeepingItemLog
        fields = ["item_name", "quantity_used", "unit", "room", "used_at", "notes"]
        widgets = {
            "item_name": forms.TextInput(attrs={"class": "form-control"}),
            "quantity_used": forms.NumberInput(attrs={"class": "form-control", "step": "0.001", "min": "0.001"}),
            "unit": forms.TextInput(attrs={"class": "form-control", "placeholder": "rolls, bars, sheets, litres"}),
            "room": forms.Select(attrs={"class": "form-select"}),
            "used_at": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["room"].queryset = Room.objects.order_by("room_number")
        self.fields["room"].required = False
        self.fields["room"].empty_label = "No room linked"
        if not self.is_bound:
            used_at = self.instance.used_at if self.instance.pk else timezone.localtime(timezone.now())
            self.initial["used_at"] = timezone.localtime(used_at).strftime("%Y-%m-%dT%H:%M")
