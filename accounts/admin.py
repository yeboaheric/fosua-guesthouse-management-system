from django.contrib import admin

from accounts.models import Employee, Rota


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = [
        "first_name",
        "last_name",
        "position",
        "contact_number",
        "start_date",
        "termination_date",
    ]
    search_fields = ["first_name", "last_name", "ghana_card_number", "position"]
    list_filter = ["position", "gender", "marital_status"]


@admin.register(Rota)
class RotaAdmin(admin.ModelAdmin):
    list_display = ["period", "operating_hours", "created_at"]
    search_fields = ["period", "operating_hours", "shift_rules"]
    filter_horizontal = ["staff_members"]
