from django.contrib import admin

from guests.models import Guest


@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "phone_number", "email", "updated_at")
    search_fields = ("first_name", "last_name", "phone_number", "ghana_card")
