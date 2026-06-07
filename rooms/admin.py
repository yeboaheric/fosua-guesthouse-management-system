from django.contrib import admin

from rooms.models import HousekeepingItemLog, Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("room_number", "room_type", "status", "base_rate", "updated_at")
    list_filter = ("room_type", "status")
    search_fields = ("room_number",)


@admin.register(HousekeepingItemLog)
class HousekeepingItemLogAdmin(admin.ModelAdmin):
    list_display = ("item_name", "quantity_used", "unit", "room", "used_at", "created_by")
    list_filter = ("unit", "used_at")
    search_fields = ("item_name", "room__room_number", "notes")
