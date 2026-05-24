"""Authorization decorators for role-based access."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def group_required(*group_names):
    """Require the logged-in user to belong to one of the given groups."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if user.is_superuser or user.groups.filter(name__in=group_names).exists():
                return view_func(request, *args, **kwargs)
            raise PermissionDenied

        return _wrapped_view

    return decorator

