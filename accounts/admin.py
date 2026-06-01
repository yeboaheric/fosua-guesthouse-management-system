from django.contrib import admin

from accounts.models import Employee, Rota


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "first_name",
        "last_name",
        "position",
        "employment_status",
        "contact_number",
        "start_date",
        "termination_date",
    ]
    search_fields = ["first_name", "last_name", "ghana_card_number", "position"]
    list_filter = ["position", "gender", "marital_status"]


@admin.register(Rota)
class RotaAdmin(admin.ModelAdmin):
    list_display = ["employee", "period", "period_start", "period_end", "operating_hours", "created_at"]
    search_fields = ["period", "shift_rules", "employee__first_name", "employee__last_name"]
    filter_horizontal = ["staff_members"]
