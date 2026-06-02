from __future__ import annotations

from django.contrib.auth.models import Group

ACCESS_MODULE_CHOICES = [
    ("dashboard", "Dashboard"),
    ("reservations", "Reservations"),
    ("rooms", "Rooms"),
    ("guests", "Guests"),
    ("payments", "Payments"),
    ("services", "Services"),
    ("housekeeping", "Housekeeping"),
    ("inventory", "Inventory"),
    ("pos", "Point of Sale"),
    ("notifications", "Notifications"),
    ("analytics", "Analytics"),
    ("reports", "Reports"),
    ("settings", "Settings"),
    ("staff_management", "Staff Management"),
    ("handovers", "Shift Handovers"),
    ("users_roles", "Users & Roles"),
]

ACTION_CHOICES = [
    ("view", "View"),
    ("create", "Create"),
    ("edit", "Edit"),
    ("delete", "Delete"),
    ("approve", "Approve"),
    ("export", "Export"),
    ("print", "Print"),
    ("manage", "Manage"),
]

MODULE_FIELDS = {
    module_name: f"{module_name}_access" for module_name, _ in ACCESS_MODULE_CHOICES
}

DEFAULT_ROLE_PRESETS = {
    "Super Administrator": {module: {action for action, _ in ACTION_CHOICES} for module, _ in ACCESS_MODULE_CHOICES},
    "Hotel Administrator": {module: {action for action, _ in ACTION_CHOICES} for module, _ in ACCESS_MODULE_CHOICES},
    "Manager": {
        "dashboard": {"view"},
        "reservations": {"view", "create", "edit", "approve", "export", "print"},
        "rooms": {"view", "edit"},
        "guests": {"view", "create", "edit"},
        "payments": {"view", "export", "print"},
        "services": {"view", "create", "edit", "approve"},
        "housekeeping": {"view", "create", "edit", "approve"},
        "inventory": {"view", "create", "edit", "export"},
        "pos": {"view", "create", "print"},
        "notifications": {"view"},
        "analytics": {"view", "export"},
        "reports": {"view", "export", "print"},
        "staff_management": {"view"},
        "handovers": {"view", "create", "edit", "approve"},
        "users_roles": {"view"},
    },
    "Receptionist": {
        "dashboard": {"view"},
        "reservations": {"view", "create", "edit", "print"},
        "rooms": {"view"},
        "guests": {"view", "create", "edit"},
        "payments": {"view", "create", "print"},
        "services": {"view", "create", "edit"},
        "housekeeping": {"view"},
        "inventory": set(),
        "pos": {"view", "create", "print"},
        "notifications": {"view"},
        "analytics": {"view"},
        "reports": set(),
        "settings": set(),
        "staff_management": set(),
        "handovers": {"view", "create"},
        "users_roles": set(),
    },
    "Accountant": {
        "dashboard": {"view"},
        "payments": {"view", "export", "print"},
        "analytics": {"view", "export"},
        "reports": {"view", "export", "print"},
        "reservations": {"view"},
        "guests": {"view"},
        "inventory": {"view", "export"},
        "pos": {"view"},
        "notifications": {"view"},
    },
    "Storekeeper": {
        "dashboard": {"view"},
        "inventory": {"view", "create", "edit", "delete", "export", "print", "manage"},
        "pos": {"view", "create", "print"},
        "reports": {"view", "export"},
        "notifications": {"view"},
    },
    "Housekeeping Supervisor": {
        "dashboard": {"view"},
        "housekeeping": {"view", "create", "edit", "approve"},
        "rooms": {"view", "edit"},
        "notifications": {"view"},
        "reports": {"view"},
        "handovers": {"view", "create", "edit"},
    },
    "Restaurant Staff": {
        "dashboard": {"view"},
        "services": {"view", "create", "edit"},
        "pos": {"view", "create", "print"},
        "inventory": {"view"},
        "notifications": {"view"},
    },
    "Bar Staff": {
        "dashboard": {"view"},
        "services": {"view", "create", "edit"},
        "pos": {"view", "create", "print"},
        "inventory": {"view"},
        "notifications": {"view"},
    },
}


def default_permissions_for_role(role_name: str) -> dict[str, set[str]]:
    preset = DEFAULT_ROLE_PRESETS.get(role_name)
    if preset is not None:
        return preset
    return {}


def access_defaults_for_roles(role_names) -> dict[str, bool]:
    permissions = {module_name: False for module_name, _ in ACCESS_MODULE_CHOICES}
    role_name_set = {str(name) for name in role_names}
    if "Super Administrator" in role_name_set or "Admin" in role_name_set:
        for module_name in permissions:
            permissions[module_name] = True
        return {f"{module}_access": enabled for module, enabled in permissions.items()}

    from accounts.models import RolePermission

    for role in Group.objects.filter(name__in=role_name_set).prefetch_related("role_permissions"):
        preset_permissions = default_permissions_for_role(role.name)
        for module_name, _ in ACCESS_MODULE_CHOICES:
            role_rows = role.role_permissions.filter(module=module_name)
            if role_rows.exists():
                if any(row.can_manage or row.can_view for row in role_rows):
                    permissions[module_name] = True
                continue
            if preset_permissions.get(module_name):
                permissions[module_name] = True

    return {f"{module}_access": enabled for module, enabled in permissions.items()}


def user_has_permission(user, module_name: str, action: str = "view") -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if user.groups.filter(name__in=["Admin", "Super Administrator"]).exists():
        return True

    access_profile = getattr(user, "access_profile", None)
    if action == "view" and access_profile is not None:
        if not getattr(access_profile, MODULE_FIELDS.get(module_name, ""), False):
            return False

    from accounts.models import RolePermission

    role_permissions = RolePermission.objects.filter(role__in=user.groups.all(), module=module_name)
    if role_permissions.exists():
        return any(permission.allows(action) for permission in role_permissions)

    for group in user.groups.all():
        preset_permissions = default_permissions_for_role(group.name)
        if action in preset_permissions.get(module_name, set()):
            return True

    if access_profile is not None and action == "view":
        return getattr(access_profile, MODULE_FIELDS.get(module_name, ""), False)

    return False


def seed_default_role_names():
    return [
        "Super Administrator",
        "Hotel Administrator",
        "Manager",
        "Receptionist",
        "Accountant",
        "Storekeeper",
        "Housekeeping Supervisor",
        "Restaurant Staff",
        "Bar Staff",
    ]
