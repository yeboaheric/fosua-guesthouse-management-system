from django import forms

from rooms.models import Room


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
