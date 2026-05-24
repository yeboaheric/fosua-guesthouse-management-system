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
    path("dashboard/reception/", reception_dashboard, name="reception-dashboard"),
]
