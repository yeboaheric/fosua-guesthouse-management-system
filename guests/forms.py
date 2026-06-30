from django import forms

from guests.models import Guest


class GuestForm(forms.ModelForm):
    class Meta:
        model = Guest
        fields = [
            "title",
            "first_name",
            "last_name",
            "phone_number",
            "email",
            "ghana_card_number",
            "ghana_card_expiry_date",
            "id_type",
            "id_number",
            "digital_address",
            "status",
        ]
        widgets = {
            "ghana_card_expiry_date": forms.DateInput(attrs={"type": "date"}),
            "id_number": forms.TextInput(
                attrs={
                    "placeholder": "Driving licence, voter ID, passport, or other ID number",
                }
            ),
        }
        labels = {
            "id_type": "Other ID type",
            "id_number": "Other ID number",
        }
        help_texts = {
            "id_type": "Use this when the guest provides a non-Ghana Card ID.",
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

    def clean(self):
        cleaned_data = super().clean()
        id_type = cleaned_data.get("id_type")
        id_number = (cleaned_data.get("id_number") or "").strip()
        if id_number and not id_type:
            self.add_error("id_type", "Select the ID type for this number.")
        if id_type and not id_number:
            self.add_error("id_number", "Enter the ID number for the selected ID type.")
        return cleaned_data
