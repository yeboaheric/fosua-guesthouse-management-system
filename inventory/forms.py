import json
from datetime import datetime
from decimal import Decimal

from django import forms
from django.utils import timezone

from accounts.formatting import format_quantity
from inventory.models import (
    CashDrawerSession,
    InventoryCategory,
    InventoryItem,
    InventorySubcategory,
    Sale,
    StockAdjustment,
    Supplier,
)


class TrimmedDecimalNumberInput(forms.NumberInput):
    def format_value(self, value):
        formatted = format_quantity(value)
        return formatted if formatted != "" else None


class InventoryCategoryForm(forms.ModelForm):
    class Meta:
        model = InventoryCategory
        fields = ["name", "category_group", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "category_group": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class InventorySubcategoryForm(forms.ModelForm):
    class Meta:
        model = InventorySubcategory
        fields = ["category", "name", "description"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "contact_person", "phone_number", "email", "address", "notes", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "contact_person": forms.TextInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = [
            "name",
            "category",
            "subcategory",
            "supplier",
            "purchase_price",
            "selling_price",
            "quantity_in_stock",
            "unit_of_measure",
            "minimum_stock_threshold",
            "status",
            "description",
            "image",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "subcategory": forms.Select(attrs={"class": "form-select"}),
            "supplier": forms.Select(attrs={"class": "form-select"}),
            "purchase_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "selling_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "quantity_in_stock": TrimmedDecimalNumberInput(attrs={"class": "form-control", "step": "0.001"}),
            "unit_of_measure": forms.Select(attrs={"class": "form-select"}),
            "minimum_stock_threshold": TrimmedDecimalNumberInput(attrs={"class": "form-control", "step": "0.001"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class StockAdjustmentForm(forms.Form):
    quantity = forms.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0.001"),
        widget=TrimmedDecimalNumberInput(),
    )
    reason = forms.CharField(max_length=120)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["quantity"].widget.attrs.update({"class": "form-control", "step": "0.001"})
        self.fields["reason"].widget.attrs.update({"class": "form-control"})


class POSCheckoutForm(forms.Form):
    payment_method = forms.ChoiceField(choices=Sale.PaymentMethod.choices, widget=forms.Select(attrs={"class": "form-select"}))
    tax_amount = forms.DecimalField(required=False, max_digits=12, decimal_places=2, initial=Decimal("0.00"), widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}))
    discount_amount = forms.DecimalField(required=False, max_digits=12, decimal_places=2, initial=Decimal("0.00"), widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}))
    amount_paid = forms.DecimalField(required=False, max_digits=12, decimal_places=2, initial=Decimal("0.00"), widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2, "class": "form-control"}))
    cart = forms.CharField(widget=forms.HiddenInput)

    def clean_cart(self):
        value = self.cleaned_data["cart"]
        if not value:
            raise forms.ValidationError("Cart is empty.")
        return value


class SaleEditForm(forms.ModelForm):
    sale_date = forms.DateField(
        label="Sale date",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    items_payload = forms.CharField(widget=forms.HiddenInput)

    class Meta:
        model = Sale
        fields = [
            "customer_name",
            "customer_phone",
            "customer_email",
            "payment_method",
            "tax_amount",
            "discount_amount",
            "amount_paid",
            "notes",
        ]
        widgets = {
            "customer_name": forms.TextInput(attrs={"class": "form-control"}),
            "customer_phone": forms.TextInput(attrs={"class": "form-control"}),
            "customer_email": forms.EmailInput(attrs={"class": "form-control"}),
            "payment_method": forms.Select(attrs={"class": "form-select"}),
            "tax_amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "discount_amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "amount_paid": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.created_at:
            self.fields["sale_date"].initial = timezone.localtime(self.instance.created_at).date()

    def save(self, commit=True):
        sale = self.instance
        for field_name in self.Meta.fields:
            setattr(sale, field_name, self.cleaned_data.get(field_name))
        existing_local_dt = timezone.localtime(sale.created_at)
        selected_date = self.cleaned_data["sale_date"]
        updated_local_dt = timezone.make_aware(
            datetime.combine(selected_date, existing_local_dt.time()),
            timezone.get_current_timezone(),
        )
        sale.created_at = updated_local_dt
        if commit:
            sale.save()
        return sale

    def clean_tax_amount(self):
        return self.cleaned_data.get("tax_amount") or Decimal("0.00")

    def clean_discount_amount(self):
        return self.cleaned_data.get("discount_amount") or Decimal("0.00")

    def clean_amount_paid(self):
        return self.cleaned_data.get("amount_paid") or Decimal("0.00")

    def clean_items_payload(self):
        raw_payload = self.cleaned_data.get("items_payload", "")
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError("The sale items could not be read. Please refresh and try again.") from exc
        if not isinstance(payload, list) or not payload:
            raise forms.ValidationError("Add at least one sale item before saving.")
        return payload


class CashDrawerOpeningForm(forms.ModelForm):
    class Meta:
        model = CashDrawerSession
        fields = ["opening_float", "opening_time", "opening_note"]
        widgets = {
            "opening_float": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "opening_time": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "opening_note": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Optional opening note"}),
        }
        labels = {
            "opening_float": "Opening float amount",
            "opening_time": "Date and time",
            "opening_note": "Opening note",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.fields["opening_time"].initial = timezone.localtime(timezone.now()).strftime("%Y-%m-%dT%H:%M")

    def clean_opening_float(self):
        value = self.cleaned_data["opening_float"]
        if value < 0:
            raise forms.ValidationError("Opening float cannot be negative.")
        return value


class CashDrawerClosingForm(forms.ModelForm):
    class Meta:
        model = CashDrawerSession
        fields = ["closing_count", "closing_time", "variance_note"]
        widgets = {
            "closing_count": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "closing_time": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "variance_note": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Required if the drawer is over or short"}),
        }
        labels = {
            "closing_count": "Closing count",
            "closing_time": "Date and time",
            "variance_note": "Variance explanation",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.fields["closing_time"].initial = timezone.localtime(timezone.now()).strftime("%Y-%m-%dT%H:%M")

    def clean_closing_count(self):
        value = self.cleaned_data["closing_count"]
        if value < 0:
            raise forms.ValidationError("Closing count cannot be negative.")
        return value

    def clean(self):
        cleaned_data = super().clean()
        closing_time = cleaned_data.get("closing_time")
        if self.instance and self.instance.pk and closing_time and closing_time < self.instance.opening_time:
            self.add_error("closing_time", "Closing time cannot be before the opening time.")
        return cleaned_data


class CashDrawerAdminEditForm(forms.ModelForm):
    class Meta:
        model = CashDrawerSession
        fields = [
            "opening_float",
            "opening_time",
            "opening_note",
            "closing_count",
            "closing_time",
            "variance_note",
        ]
        widgets = {
            "opening_float": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "opening_time": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "opening_note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "closing_count": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "closing_time": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "variance_note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("opening_time", "closing_time"):
            field_value = getattr(self.instance, field_name, None)
            if field_value and not self.is_bound:
                self.fields[field_name].initial = timezone.localtime(field_value).strftime("%Y-%m-%dT%H:%M")

    def clean(self):
        cleaned_data = super().clean()
        opening_float = cleaned_data.get("opening_float")
        closing_count = cleaned_data.get("closing_count")
        opening_time = cleaned_data.get("opening_time")
        closing_time = cleaned_data.get("closing_time")
        if opening_float is not None and opening_float < 0:
            self.add_error("opening_float", "Opening float cannot be negative.")
        if closing_count is not None and closing_count < 0:
            self.add_error("closing_count", "Closing count cannot be negative.")
        if opening_time and closing_time and closing_time < opening_time:
            self.add_error("closing_time", "Closing time cannot be before the opening time.")
        return cleaned_data
