from accounts.models import Notification
from accounts.permissions import user_has_permission


def notification_badge(request):
    user = getattr(request, "user", None)
    if not getattr(user, "is_authenticated", False):
        return {"unread_notifications_count": 0}

    if not user_has_permission(user, "notifications", "view"):
        return {"unread_notifications_count": 0}

    return {
        "unread_notifications_count": Notification.objects.filter(
            user=user,
            read_at__isnull=True,
        ).count()
    }
