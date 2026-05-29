from django.urls import path

from accounts.views import (
    FosuaLoginView,
    FosuaLogoutView,
    admin_dashboard,
    admin_reports_export_balances_csv,
    admin_reports_export_daily_csv,
    admin_reports,
    dashboard,
    home_redirect,
    hr_employee_create,
    hr_employee_list,
    hr_employee_update,
    hr_employee_delete,
    hr_rota_create,
    hr_rota_list,
    hr_rota_update,
    reception_dashboard,
)

urlpatterns = [
    path("", home_redirect, name="home"),
    path("login/", FosuaLoginView.as_view(), name="login"),
    path("logout/", FosuaLogoutView.as_view(), name="logout"),
    path("dashboard/", dashboard, name="dashboard"),
    path("dashboard/admin/", admin_dashboard, name="admin-dashboard"),
    path("dashboard/admin/reports/", admin_reports, name="admin-reports"),
    path(
        "dashboard/admin/reports/export/daily/",
        admin_reports_export_daily_csv,
        name="admin-reports-export-daily",
    ),
    path(
        "dashboard/admin/reports/export/balances/",
        admin_reports_export_balances_csv,
        name="admin-reports-export-balances",
    ),
    path("dashboard/admin/hr/", hr_employee_list, name="hr-list"),
    path("dashboard/admin/hr/new/", hr_employee_create, name="hr-create"),
    path("dashboard/admin/hr/<int:pk>/edit/", hr_employee_update, name="hr-update"),
    path("dashboard/admin/hr/<int:pk>/delete/", hr_employee_delete, name="hr-delete"),
    path("dashboard/admin/hr/rotas/", hr_rota_list, name="hr-rota-list"),
    path("dashboard/admin/hr/rotas/new/", hr_rota_create, name="hr-rota-create"),
    path("dashboard/admin/hr/rotas/<int:pk>/edit/", hr_rota_update, name="hr-rota-update"),
    path("dashboard/reception/", reception_dashboard, name="reception-dashboard"),
]
