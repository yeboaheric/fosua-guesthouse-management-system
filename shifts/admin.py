from django.contrib import admin

from shifts.models import ShiftHandover, ShiftHandoverUpdate


@admin.register(ShiftHandover)
class ShiftHandoverAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "started_at",
        "ended_at",
        "prepared_by",
        "check_ins_count",
        "check_outs_count",
        "reservations_count",
        "cancellations_count",
    )
    list_filter = ("started_at", "ended_at")
    search_fields = ("prepared_by__username",)


@admin.register(ShiftHandoverUpdate)
class ShiftHandoverUpdateAdmin(admin.ModelAdmin):
    list_display = ("handover", "author", "created_at")
    search_fields = ("handover__id", "author__username", "note")
