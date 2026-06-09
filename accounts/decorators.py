"""Authorization decorators for role-based access."""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from accounts.models import UserAccessProfile
from accounts.permissions import access_defaults_for_roles, user_has_permission


def _default_access_for_user(user):
    return access_defaults_for_roles(user.groups.values_list("name", flat=True))


def group_required(*group_names, module=None, action="view", denied_redirect=None, denied_message=""):
    """Require the logged-in user to belong to one of the given groups."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if user.is_superuser:
                return view_func(request, *args, **kwargs)
            is_authorized = True
            if module:
                UserAccessProfile.objects.get_or_create(
                    user=user,
                    defaults=_default_access_for_user(user),
                )
                is_authorized = user_has_permission(user, module, action)
            elif group_names:
                is_authorized = user.groups.filter(name__in=group_names).exists()
            if not is_authorized:
                if denied_redirect:
                    if denied_message:
                        messages.error(request, denied_message)
                    return redirect(denied_redirect)
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
