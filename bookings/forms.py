from django import forms

from bookings.models import Booking
from bookings.models import Payment
from rooms.models import Room


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = [
            "guest",
            "room",
            "check_in",
            "check_out",
            "adults",
            "children",
            "status",
            "total_amount",
            "notes",
        ]
        widgets = {
            "check_in": forms.DateInput(attrs={"type": "date"}),
            "check_out": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["room"].queryset = Room.objects.exclude(
            status=Room.RoomStatus.MAINTENANCE
        )
        for field in self.fields.values():
            css_class = (
                "form-select"
                if isinstance(field.widget, forms.Select)
                else "form-control"
            )
            field.widget.attrs["class"] = css_class


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["amount", "method", "reference", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
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
