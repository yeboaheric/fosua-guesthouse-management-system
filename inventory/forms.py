from decimal import Decimal

from django import forms

from inventory.models import (
    InventoryCategory,
    InventoryItem,
    InventorySubcategory,
    Sale,
    StockAdjustment,
    Supplier,
)


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
            "quantity_in_stock": forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}),
            "unit_of_measure": forms.Select(attrs={"class": "form-select"}),
            "minimum_stock_threshold": forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class StockAdjustmentForm(forms.Form):
    quantity = forms.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"))
    reason = forms.CharField(max_length=120)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["quantity"].widget.attrs.update({"class": "form-control", "step": "0.001"})
        self.fields["reason"].widget.attrs.update({"class": "form-control"})


class POSCheckoutForm(forms.Form):
    customer_name = forms.CharField(required=False, max_length=160)
    customer_phone = forms.CharField(required=False, max_length=40)
    customer_email = forms.EmailField(required=False)
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
