from datetime import time

from django import forms

from bookings.models import Booking
from bookings.models import EventBooking
from bookings.models import EventPayment
from bookings.models import Payment
from rooms.models import Room


class RoomRateSelect(forms.Select):
    def __init__(self, *args, **kwargs):
        self.room_rates = {}
        super().__init__(*args, **kwargs)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        key = str(value) if value is not None else ""
        if key in self.room_rates:
            option["attrs"]["data-rate"] = str(self.room_rates[key])
        return option


class RoomRateSelectMultiple(forms.SelectMultiple):
    def __init__(self, *args, **kwargs):
        self.room_rates = {}
        super().__init__(*args, **kwargs)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        key = str(value) if value is not None else ""
        if key in self.room_rates:
            option["attrs"]["data-rate"] = str(self.room_rates[key])
        return option


class BookingForm(forms.ModelForm):
    rooms = forms.ModelMultipleChoiceField(
        queryset=Room.objects.none(),
        required=False,
        widget=RoomRateSelectMultiple(),
        help_text="Select one or more available rooms for the same guest and date range.",
    )

    class Meta:
        model = Booking
        fields = [
            "guest",
            "room",
            "rooms",
            "check_in",
            "check_in_time",
            "check_out",
            "check_out_time",
            "adults",
            "children",
            "status",
            "total_amount",
            "notes",
        ]
        widgets = {
            "room": RoomRateSelect(),
            "check_in": forms.DateInput(attrs={"type": "date"}),
            "check_in_time": forms.TimeInput(attrs={"type": "time"}),
            "check_out": forms.DateInput(attrs={"type": "date"}),
            "check_out_time": forms.TimeInput(attrs={"type": "time"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        available_rooms = Room.objects.filter(status=Room.RoomStatus.AVAILABLE).order_by(
            "room_number"
        )
        self.fields["rooms"].queryset = available_rooms
        self.fields["rooms"].widget.room_rates = {
            str(room.pk): room.base_rate for room in available_rooms
        }

        if self.instance and self.instance.pk:
            room_queryset = (
                Room.objects.filter(status=Room.RoomStatus.AVAILABLE)
                | Room.objects.filter(pk=self.instance.room_id)
            ).order_by("room_number")
            self.fields["room"].queryset = room_queryset
            self.fields["room"].widget.room_rates = {
                str(room.pk): room.base_rate for room in room_queryset
            }
            self.fields.pop("rooms")
        else:
            self.fields.pop("room")

        if not self.instance or not self.instance.pk:
            self.initial.setdefault("check_in_time", time(14, 0))
            self.initial.setdefault("check_out_time", time(11, 0))

        self.fields["total_amount"].required = False
        self.fields["total_amount"].widget.attrs["readonly"] = True

        for field in self.fields.values():
            css_class = (
                "form-select"
                if isinstance(field.widget, forms.Select)
                else "form-control"
            )
            field.widget.attrs["class"] = css_class

    def clean(self):
        cleaned_data = super().clean()
        if not (self.instance and self.instance.pk):
            rooms = cleaned_data.get("rooms")
            if not rooms:
                raise forms.ValidationError("Select at least one available room.")
        return cleaned_data


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


class PaymentAdminEditForm(forms.ModelForm):
    paid_at = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        input_formats=["%Y-%m-%dT%H:%M"],
    )

    class Meta:
        model = Payment
        fields = ["amount", "method", "reference", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.paid_at:
            self.initial["paid_at"] = self.instance.paid_at.astimezone().strftime("%Y-%m-%dT%H:%M")
        for field_name, field in self.fields.items():
            if field_name == "paid_at":
                field.widget.attrs["class"] = "form-control"
                continue
            css_class = (
                "form-select"
                if isinstance(field.widget, forms.Select)
                else "form-control"
            )
            field.widget.attrs["class"] = css_class

    def save(self, commit=True):
        payment = super().save(commit=False)
        payment.paid_at = self.cleaned_data["paid_at"]
        if commit:
            payment.save()
        return payment


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


class EventPaymentAdminEditForm(forms.ModelForm):
    paid_at = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        input_formats=["%Y-%m-%dT%H:%M"],
    )

    class Meta:
        model = EventPayment
        fields = ["amount", "method", "reference", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.paid_at:
            self.initial["paid_at"] = self.instance.paid_at.astimezone().strftime("%Y-%m-%dT%H:%M")
        for field_name, field in self.fields.items():
            if field_name == "paid_at":
                field.widget.attrs["class"] = "form-control"
                continue
            css_class = (
                "form-select"
                if isinstance(field.widget, forms.Select)
                else "form-control"
            )
            field.widget.attrs["class"] = css_class

    def save(self, commit=True):
        payment = super().save(commit=False)
        payment.paid_at = self.cleaned_data["paid_at"]
        if commit:
            payment.save()
        return payment
