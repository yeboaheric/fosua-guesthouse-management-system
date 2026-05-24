from django import forms

from bookings.models import Booking
from bookings.models import EventBooking
from bookings.models import EventPayment
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


class EventBookingForm(forms.ModelForm):
    class Meta:
        model = EventBooking
        fields = [
            "guest",
            "event_space_name",
            "event_title",
            "purpose",
            "expected_guests",
            "event_start",
            "event_end",
            "setup_style",
            "needs_catering",
            "needs_audio_visual",
            "status",
            "total_amount",
            "notes",
        ]
        widgets = {
            "purpose": forms.Textarea(attrs={"rows": 3}),
            "event_start": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "event_end": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["event_start"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["event_end"].input_formats = ["%Y-%m-%dT%H:%M"]
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
                continue

            css_class = (
                "form-select"
                if isinstance(field.widget, forms.Select)
                else "form-control"
            )
            field.widget.attrs["class"] = css_class


class EventPaymentForm(forms.ModelForm):
    class Meta:
        model = EventPayment
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
