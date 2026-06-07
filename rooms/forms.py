from django import forms
from django.utils import timezone

from accounts.formatting import format_quantity
from rooms.models import HousekeepingItemLog, Room


class TrimmedDecimalNumberInput(forms.NumberInput):
    def format_value(self, value):
        formatted = format_quantity(value)
        return formatted if formatted != "" else None


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
        fields = [
            "item_name",
            "initial_quantity",
            "quantity_used",
            "quantity_in_stock",
            "low_stock_threshold",
            "unit",
            "room",
            "used_at",
            "notes",
        ]
        widgets = {
            "item_name": forms.TextInput(attrs={"class": "form-control"}),
            "initial_quantity": TrimmedDecimalNumberInput(attrs={"class": "form-control", "step": "0.001", "min": "0.001"}),
            "quantity_used": TrimmedDecimalNumberInput(attrs={"class": "form-control", "step": "0.001", "min": "0.001"}),
            "quantity_in_stock": TrimmedDecimalNumberInput(
                attrs={"class": "form-control", "step": "0.001", "readonly": "readonly"}
            ),
            "low_stock_threshold": TrimmedDecimalNumberInput(
                attrs={"class": "form-control", "step": "0.001", "min": "0", "placeholder": "Optional custom threshold"}
            ),
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
        self.fields["quantity_in_stock"].required = False
        if not self.is_bound:
            used_at = self.instance.used_at if self.instance.pk else timezone.localtime(timezone.now())
            self.initial["used_at"] = timezone.localtime(used_at).strftime("%Y-%m-%dT%H:%M")
            initial_quantity = self.instance.initial_quantity if self.instance.pk else 0
            quantity_used = self.instance.quantity_used if self.instance.pk else 0
            self.initial["quantity_in_stock"] = initial_quantity - quantity_used

    def clean(self):
        cleaned_data = super().clean()
        initial_quantity = cleaned_data.get("initial_quantity")
        quantity_used = cleaned_data.get("quantity_used")
        if initial_quantity is not None and quantity_used is not None:
            cleaned_data["quantity_in_stock"] = initial_quantity - quantity_used
        return cleaned_data
