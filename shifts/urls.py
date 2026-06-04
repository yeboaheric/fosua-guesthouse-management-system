from django.urls import path

from shifts.views import (
    handover_create,
    handover_detail,
    handover_list,
    roster_report,
    roster_detail,
    roster_export_excel,
)

urlpatterns = [
    path("", handover_list, name="handover-list"),
    path("new/", handover_create, name="handover-create"),
    path("<int:pk>/", handover_detail, name="handover-detail"),
    path("roster/", roster_report, name="roster-report"),
    path("roster/<int:pk>/", roster_detail, name="roster-detail"),
    path("roster/export/excel/", roster_export_excel, name="roster-export-excel"),
]
