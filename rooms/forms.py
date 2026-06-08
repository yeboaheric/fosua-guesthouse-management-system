from django import forms
from django.utils import timezone

from accounts.formatting import format_quantity
from rooms.models import HousekeepingItem, HousekeepingItemLog, Room


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
            "item",
            "quantity_used",
            "room",
            "used_at",
            "notes",
        ]
        widgets = {
            "item": forms.Select(attrs={"class": "form-select"}),
            "quantity_used": TrimmedDecimalNumberInput(attrs={"class": "form-control", "step": "0.001", "min": "0.001"}),
            "room": forms.Select(attrs={"class": "form-select"}),
            "used_at": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["item"].queryset = HousekeepingItem.objects.order_by("name")
        self.fields["item"].empty_label = "Select an item"
        self.fields["room"].queryset = Room.objects.order_by("room_number")
        self.fields["room"].required = False
        self.fields["room"].empty_label = "No room linked"
        if not self.is_bound:
            used_at = self.instance.used_at if self.instance.pk else timezone.localtime(timezone.now())
            self.initial["used_at"] = timezone.localtime(used_at).strftime("%Y-%m-%dT%H:%M")

    def clean(self):
        cleaned_data = super().clean()
        item = cleaned_data.get("item")
        quantity_used = cleaned_data.get("quantity_used")
        if item is not None and quantity_used is not None:
            available_stock = item.quantity_in_stock
            if self.instance.pk and self.instance.item_id == item.pk:
                available_stock += self.instance.quantity_used
            if quantity_used > available_stock:
                self.add_error("quantity_used", "Quantity used cannot be greater than the available quantity in stock.")
        return cleaned_data


class HousekeepingItemForm(forms.ModelForm):
    class Meta:
        model = HousekeepingItem
        fields = [
            "name",
            "initial_quantity",
            "low_stock_threshold",
            "unit",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "initial_quantity": TrimmedDecimalNumberInput(attrs={"class": "form-control", "step": "0.001", "min": "0.001"}),
            "low_stock_threshold": TrimmedDecimalNumberInput(
                attrs={"class": "form-control", "step": "0.001", "min": "0", "placeholder": "Optional custom threshold"}
            ),
            "unit": forms.TextInput(attrs={"class": "form-control", "placeholder": "rolls, bars, sheets, litres"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["low_stock_threshold"].required = False
