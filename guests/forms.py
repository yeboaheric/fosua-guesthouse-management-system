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
            "digital_address",
            "status",
        ]
        widgets = {
            "ghana_card_expiry_date": forms.DateInput(attrs={"type": "date"}),
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
