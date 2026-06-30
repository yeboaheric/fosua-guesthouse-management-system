from __future__ import annotations

import threading

from django.utils import timezone

from accounts.models import AuditLog

_thread_local = threading.local()

def set_current_request(request):
    setattr(_thread_local, "request", request)


def get_current_request():
    return getattr(_thread_local, "request", None)


def get_current_user():
    request = get_current_request()
    if request is not None and getattr(request, "user", None) and request.user.is_authenticated:
        return request.user
    return None


def client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def module_from_url_name(url_name: str | None) -> str:
    url_name = url_name or ""
    mapping = {
        "users-roles-center": "users_roles",
        "hr-list": "staff_management",
        "hr-create": "staff_management",
        "hr-update": "staff_management",
        "hr-detail": "staff_management",
        "hr-delete": "staff_management",
        "hr-rota-list": "staff_management",
        "hr-rota-create": "staff_management",
        "hr-rota-update": "staff_management",
        "hr-rota-detail": "staff_management",
        "booking-list": "reservations",
        "front-desk-center": "reservations",
        "booking-create": "reservations",
        "booking-update": "reservations",
        "booking-detail": "reservations",
        "booking-payments": "payments",
        "booking-payment-update": "payments",
        "booking-payment-delete": "payments",
        "booking-confirm": "reservations",
        "booking-check-in": "reservations",
        "booking-check-out": "reservations",
        "booking-cancel": "reservations",
        "room-list": "rooms",
        "room-create": "rooms",
        "room-update": "rooms",
        "room-availability": "rooms",
        "guest-list": "guests",
        "guest-create": "guests",
        "guest-update": "guests",
        "payments-center": "payments",
        "services-center": "services",
        "event-booking-list": "services",
        "event-booking-create": "services",
        "event-booking-update": "services",
        "event-booking-payments": "services",
        "event-payment-update": "payments",
        "event-payment-delete": "payments",
        "housekeeping-dashboard": "housekeeping",
        "housekeeping-center": "housekeeping",
        "housekeeping-log-edit": "housekeeping",
        "housekeeping-log-delete": "housekeeping",
        "housekeeping-report-export": "housekeeping",
        "operations-overview": "dashboard",
        "inventory-dashboard": "inventory",
        "inventory-categories": "inventory",
        "inventory-subcategories": "inventory",
        "inventory-suppliers": "inventory",
        "inventory-items": "inventory",
        "inventory-transactions": "inventory",
        "inventory-reports": "inventory",
        "inventory-sales": "inventory",
        "inventory-sale-detail": "inventory",
        "inventory-sale-update": "pos",
        "inventory-sale-delete": "pos",
        "inventory-pos": "pos",
        "inventory-pos-checkout": "pos",
        "admin-reports": "reports",
        "admin-report-detail": "reports",
        "admin-reports-export-all": "reports",
        "admin-reports-export-daily": "reports",
        "admin-reports-export-balances": "reports",
        "admin-reports-export-section": "reports",
        "analytics-center": "analytics",
        "analytics-export": "analytics",
        "notifications-center": "notifications",
        "settings-center": "settings",
        "handover-list": "handovers",
        "handover-create": "handovers",
        "handover-detail": "handovers",
    }
    return mapping.get(url_name, "")


def log_audit_event(
    *,
    request=None,
    user=None,
    action=AuditLog.ActionType.OTHER,
    module="",
    object_repr="",
    object_id="",
    path="",
    ip_address=None,
    status_code=None,
    details=None,
    mark_request=True,
):
    if request is not None:
        if user is None and getattr(request, "user", None) and request.user.is_authenticated:
            user = request.user
        path = path or request.path
        ip_address = ip_address or client_ip(request)
        if not module:
            module = module_from_url_name(getattr(getattr(request, "resolver_match", None), "url_name", None))
    if user is not None and not getattr(user, "is_authenticated", False):
        user = None
    payload = details or {}
    event = AuditLog.objects.create(
        user=user,
        action=action,
        module=module,
        object_repr=object_repr,
        object_id=str(object_id) if object_id is not None else "",
        path=path,
        ip_address=ip_address,
        status_code=status_code,
        details=payload,
        created_at=timezone.now(),
    )
    if request is not None and mark_request:
        setattr(request, "_audit_logged", True)
    return event
