from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from accounts.audit import log_audit_event
from accounts.models import AuditLog
from accounts.permissions import clear_permission_snapshot, store_permission_snapshot


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    store_permission_snapshot(request, user)
    log_audit_event(
        request=request,
        user=user,
        action=AuditLog.ActionType.LOGIN,
        module="dashboard",
        object_repr=user.get_username(),
        details={"event": "user_login"},
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    clear_permission_snapshot(request)
    log_audit_event(
        request=request,
        user=user,
        action=AuditLog.ActionType.LOGOUT,
        module="dashboard",
        object_repr=getattr(user, "get_username", lambda: "")(),
        details={"event": "user_logout"},
    )


@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    # Never persist submitted passwords or other credential fields.
    username = str((credentials or {}).get("username", ""))[:150]
    log_audit_event(
        request=request,
        action=AuditLog.ActionType.LOGIN,
        module="dashboard",
        object_repr=username,
        details={"event": "login_failed", "username": username},
        mark_request=False,
    )
