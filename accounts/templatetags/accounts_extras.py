from django import template

from accounts.formatting import format_quantity
from accounts.permissions import user_has_permission

register = template.Library()


@register.filter
def has_group(user, group_name):
    if not user.is_authenticated:
        return False
    return user.groups.filter(name=group_name).exists()


@register.filter
def nav_active(request, names):
    current = getattr(getattr(request, "resolver_match", None), "url_name", "") or ""
    target_names = {name.strip() for name in str(names).split()}
    return "active" if current in target_names else ""


@register.filter
def get_item(mapping, key):
    if mapping is None:
        return None
    return mapping.get(key)


@register.filter
def can_access_module(user, module_name):
    return user_has_permission(user, module_name, "view")


@register.filter
def get_field(form, field_name):
    try:
        return form[field_name]
    except Exception:
        return None


@register.filter
def quantity(value):
    return format_quantity(value)
