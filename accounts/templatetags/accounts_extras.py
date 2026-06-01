from django import template

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
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.groups.filter(name="Admin").exists():
        return True
    access_profile = getattr(user, "access_profile", None)
    if access_profile is None:
        return False
    return access_profile.has_module_access(module_name)
