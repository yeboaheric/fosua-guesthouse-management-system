"""Authorization decorators for role-based access."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from accounts.models import UserAccessProfile


def _default_access_for_user(user):
    if user.is_superuser or user.groups.filter(name="Admin").exists():
        return {
            "dashboard_access": True,
            "reservations_access": True,
            "rooms_access": True,
            "guests_access": True,
            "payments_access": True,
            "services_access": True,
            "housekeeping_access": True,
            "inventory_access": True,
            "pos_access": True,
            "notifications_access": True,
            "analytics_access": True,
            "reports_access": True,
            "settings_access": True,
            "staff_management_access": True,
            "handovers_access": True,
            "users_roles_access": True,
        }
    if user.groups.filter(name="Receptionist").exists():
        return {
            "dashboard_access": True,
            "reservations_access": True,
            "rooms_access": True,
            "guests_access": True,
            "payments_access": True,
            "services_access": True,
            "housekeeping_access": True,
            "inventory_access": False,
            "pos_access": True,
            "notifications_access": True,
            "analytics_access": True,
            "reports_access": False,
            "settings_access": False,
            "staff_management_access": False,
            "handovers_access": True,
            "users_roles_access": False,
        }
    return {"dashboard_access": True}


def group_required(*group_names, module=None):
    """Require the logged-in user to belong to one of the given groups."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if user.is_superuser or user.groups.filter(name="Admin").exists():
                return view_func(request, *args, **kwargs)
            if not user.groups.filter(name__in=group_names).exists():
                raise PermissionDenied
            if module:
                access_profile, _ = UserAccessProfile.objects.get_or_create(
                    user=user,
                    defaults=_default_access_for_user(user),
                )
                if not access_profile.has_module_access(module):
                    raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
