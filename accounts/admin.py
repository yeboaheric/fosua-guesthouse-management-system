from django.contrib import admin

from accounts.models import (
    AttendanceRecord,
    DisciplinaryRecord,
    Employee,
    EmployeeDocument,
    EmployeeQualification,
    Expense,
    EmploymentHistoryEntry,
    LeaveRequest,
    Notification,
    OwnerWithdrawal,
    PayrollRecord,
    PerformanceReview,
    Rota,
    StatusHistory,
    TrainingRecord,
)
from rooms.models import MaintenanceRequest


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = [
        "employee_id",
        "title",
        "first_name",
        "last_name",
        "department",
        "position",
        "employment_status",
        "contact_number",
        "start_date",
        "termination_date",
    ]
    search_fields = ["employee_id", "first_name", "last_name", "ghana_card_number", "position", "department"]
    list_filter = ["position", "gender", "marital_status", "employment_status", "department"]


@admin.register(Rota)
class RotaAdmin(admin.ModelAdmin):
    list_display = ["employee", "period", "period_start", "period_end", "operating_hours", "created_at"]
    search_fields = ["period", "shift_rules", "employee__first_name", "employee__last_name"]
    filter_horizontal = ["staff_members"]


@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = ["employee", "document_type", "title", "created_at"]
    search_fields = ["employee__first_name", "employee__last_name", "title", "description"]
    list_filter = ["document_type", "created_at"]


@admin.register(EmployeeQualification)
class EmployeeQualificationAdmin(admin.ModelAdmin):
    list_display = ["employee", "qualification_name", "institution", "expiry_date"]
    search_fields = ["employee__first_name", "employee__last_name", "qualification_name", "institution", "certificate_number"]
    list_filter = ["expiry_date", "certification_date"]


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ["employee", "leave_type", "start_date", "end_date", "approval_status"]
    search_fields = ["employee__first_name", "employee__last_name", "reason"]
    list_filter = ["leave_type", "approval_status", "start_date", "end_date"]


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ["employee", "work_date", "shift_type", "status"]
    search_fields = ["employee__first_name", "employee__last_name", "notes"]
    list_filter = ["shift_type", "status", "work_date"]


@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
    list_display = ["employee", "pay_period_start", "pay_period_end", "net_pay", "payment_status"]
    search_fields = ["employee__first_name", "employee__last_name", "notes"]
    list_filter = ["payment_status", "pay_period_start", "pay_period_end"]


@admin.register(PerformanceReview)
class PerformanceReviewAdmin(admin.ModelAdmin):
    list_display = ["employee", "review_date", "rating", "reviewer"]
    search_fields = ["employee__first_name", "employee__last_name", "summary", "strengths", "improvement_areas"]
    list_filter = ["review_date", "rating"]


@admin.register(DisciplinaryRecord)
class DisciplinaryRecordAdmin(admin.ModelAdmin):
    list_display = ["employee", "incident_date", "record_type", "resolved"]
    search_fields = ["employee__first_name", "employee__last_name", "details", "action_taken"]
    list_filter = ["record_type", "resolved", "incident_date"]


@admin.register(TrainingRecord)
class TrainingRecordAdmin(admin.ModelAdmin):
    list_display = ["employee", "training_name", "provider", "completion_date", "expiry_date"]
    search_fields = ["employee__first_name", "employee__last_name", "training_name", "provider"]
    list_filter = ["completion_date", "expiry_date"]


@admin.register(EmploymentHistoryEntry)
class EmploymentHistoryEntryAdmin(admin.ModelAdmin):
    list_display = ["employee", "change_type", "effective_date", "created_by"]
    search_fields = ["employee__first_name", "employee__last_name", "description"]
    list_filter = ["change_type", "effective_date"]


@admin.register(StatusHistory)
class StatusHistoryAdmin(admin.ModelAdmin):
    list_display = ["object_repr", "previous_status", "new_status", "changed_by", "changed_at"]
    search_fields = ["object_repr", "previous_status", "new_status", "changed_by__username"]
    list_filter = ["changed_at"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "level", "read_at", "created_at"]
    search_fields = ["title", "message"]
    list_filter = ["level", "read_at", "created_at"]


@admin.register(OwnerWithdrawal)
class OwnerWithdrawalAdmin(admin.ModelAdmin):
    list_display = ["created_at", "amount", "collection_method", "collected_by", "recorded_by"]
    search_fields = ["reason", "collected_by", "recorded_by__username", "recorded_by__first_name", "recorded_by__last_name"]
    list_filter = ["created_at", "collection_method"]


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["date", "category", "amount", "payment_method", "recorded_by"]
    search_fields = ["category", "description", "recorded_by__username", "recorded_by__first_name", "recorded_by__last_name"]
    list_filter = ["date", "category", "payment_method"]


@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = ["room", "status", "requested_by", "assigned_to", "created_at"]
    search_fields = ["room__room_number", "description", "requested_by__username", "assigned_to__username"]
    list_filter = ["status", "created_at"]
