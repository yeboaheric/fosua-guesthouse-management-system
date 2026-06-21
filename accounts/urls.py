from django.urls import path
from django.contrib.auth.views import (
    PasswordChangeDoneView,
    PasswordChangeView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)

from accounts.views import (
    FosuaLoginView,
    FosuaLogoutView,
    admin_dashboard,
    admin_dashboard_activity_feed,
    admin_reports_export_all_excel,
    admin_reports_export_balances_csv,
    admin_reports_export_daily_csv,
    admin_reports_export_section_excel,
    admin_reports,
    dashboard,
    global_search,
    home_redirect,
    hr_employee_create,
    hr_employee_detail,
    hr_employee_section,
    hr_employee_list,
    hr_employee_update,
    hr_employee_delete,
    hr_rota_create,
    hr_rota_detail,
    hr_rota_list,
    hr_rota_update,
    housekeeping_center,
    notifications_center,
    notification_mark_read,
    analytics_center,
    analytics_export,
    payments_center,
    sales_deposits_center,
    sales_deposit_delete,
    sales_deposit_update,
    sales_deposits_export_xlsx,
    users_roles_center,
    services_center,
    settings_center,
    reception_dashboard,
)


class FosuaPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset_form.html"
    email_template_name = "accounts/password_reset_email.html"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = "/password-reset/done/"


class FosuaPasswordResetDoneView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class FosuaPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = "/password-reset/complete/"


class FosuaPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


class FosuaPasswordChangeView(PasswordChangeView):
    template_name = "accounts/password_change_form.html"
    success_url = "/password-change/done/"


class FosuaPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = "accounts/password_change_done.html"

urlpatterns = [
    path("", home_redirect, name="home"),
    path("login/", FosuaLoginView.as_view(), name="login"),
    path("logout/", FosuaLogoutView.as_view(), name="logout"),
    path("password-reset/", FosuaPasswordResetView.as_view(), name="password_reset"),
    path("password-reset/done/", FosuaPasswordResetDoneView.as_view(), name="password_reset_done"),
    path("password-reset/confirm/<uidb64>/<token>/", FosuaPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password-reset/complete/", FosuaPasswordResetCompleteView.as_view(), name="password_reset_complete"),
    path("password-change/", FosuaPasswordChangeView.as_view(), name="password_change"),
    path("password-change/done/", FosuaPasswordChangeDoneView.as_view(), name="password_change_done"),
    path("dashboard/", dashboard, name="dashboard"),
    path("dashboard/admin/", admin_dashboard, name="admin-dashboard"),
    path("dashboard/admin/activity-feed/", admin_dashboard_activity_feed, name="admin-dashboard-activity-feed"),
    path("dashboard/admin/reports/", admin_reports, name="admin-reports"),
    path(
        "dashboard/admin/reports/export/all/xlsx/",
        admin_reports_export_all_excel,
        name="admin-reports-export-all",
    ),
    path(
        "dashboard/admin/reports/export/<slug:section>/xlsx/",
        admin_reports_export_section_excel,
        name="admin-reports-export-section",
    ),
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
    path("dashboard/search/", global_search, name="global-search"),
    path("dashboard/payments/", payments_center, name="payments-center"),
    path("dashboard/sales-deposits/", sales_deposits_center, name="sales-deposits-center"),
    path("dashboard/sales-deposits/export/xlsx/", sales_deposits_export_xlsx, name="sales-deposits-export-xlsx"),
    path("dashboard/sales-deposits/<int:pk>/edit/", sales_deposit_update, name="sales-deposit-update"),
    path("dashboard/sales-deposits/<int:pk>/delete/", sales_deposit_delete, name="sales-deposit-delete"),
    path("dashboard/services/", services_center, name="services-center"),
    path("dashboard/housekeeping/", housekeeping_center, name="housekeeping-center"),
    path("dashboard/notifications/", notifications_center, name="notifications-center"),
    path("dashboard/notifications/read/<int:pk>/", notification_mark_read, name="notification-mark-read"),
    path("dashboard/analytics/", analytics_center, name="analytics-center"),
    path("dashboard/analytics/export/<slug:fmt>/", analytics_export, name="analytics-export"),
    path("dashboard/settings/", settings_center, name="settings-center"),
    path("dashboard/users-roles/", users_roles_center, name="users-roles-center"),
    path("dashboard/admin/hr/", hr_employee_list, name="hr-list"),
    path("dashboard/admin/hr/new/", hr_employee_create, name="hr-create"),
    path("dashboard/admin/hr/<int:pk>/edit/", hr_employee_update, name="hr-update"),
    path("dashboard/admin/hr/<int:pk>/delete/", hr_employee_delete, name="hr-delete"),
    path("dashboard/admin/hr/<int:pk>/", hr_employee_detail, name="hr-detail"),
    path("dashboard/admin/hr/<int:pk>/<slug:section>/", hr_employee_section, name="hr-employee-section"),
    path("dashboard/admin/hr/rotas/", hr_rota_list, name="hr-rota-list"),
    path("dashboard/admin/hr/rotas/new/", hr_rota_create, name="hr-rota-create"),
    path("dashboard/admin/hr/rotas/<int:pk>/", hr_rota_detail, name="hr-rota-detail"),
    path("dashboard/admin/hr/rotas/<int:pk>/edit/", hr_rota_update, name="hr-rota-update"),
    path("dashboard/reception/", reception_dashboard, name="reception-dashboard"),
]
