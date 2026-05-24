from django.contrib import admin

from rooms.models import Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("room_number", "room_type", "status", "base_rate", "updated_at")
    list_filter = ("room_type", "status")
    search_fields = ("room_number",)
