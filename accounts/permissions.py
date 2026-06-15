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

ADMIN_ROLE_NAMES = ("Admin", "Super Administrator", "Hotel Administrator")

MODULE_FIELDS = {
    module_name: f"{module_name}_access" for module_name, _ in ACCESS_MODULE_CHOICES
}

PERMISSION_SNAPSHOT_SESSION_KEY = "fg_permission_snapshot"
PERMISSION_SNAPSHOT_REQUEST_ATTR = "_fg_permission_snapshot"

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
        "housekeeping": set(),
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


def _all_actions() -> set[str]:
    return {action for action, _ in ACTION_CHOICES}


def build_permission_snapshot(user) -> dict:
    module_access = access_defaults_for_roles(user.groups.values_list("name", flat=True))
    module_actions = {module_name: set() for module_name, _ in ACCESS_MODULE_CHOICES}

    if not user.is_authenticated:
        return {
            "user_id": None,
            "module_access": module_access,
            "module_actions": {module: {} for module in module_actions},
        }

    if user.is_superuser or user.groups.filter(name__in=["Admin", "Super Administrator"]).exists():
        for module_name in module_actions:
            module_actions[module_name] = _all_actions()
            module_access[f"{module_name}_access"] = True
    else:
        from accounts.models import RolePermission

        role_permissions = RolePermission.objects.filter(role__in=user.groups.all())
        if role_permissions.exists():
            for permission in role_permissions:
                if permission.can_manage:
                    module_actions[permission.module].update(_all_actions())
                    module_access[f"{permission.module}_access"] = True
                    continue
                if permission.can_view:
                    module_actions[permission.module].add("view")
                    module_access[f"{permission.module}_access"] = True
                if permission.can_create:
                    module_actions[permission.module].add("create")
                if permission.can_edit:
                    module_actions[permission.module].add("edit")
                if permission.can_delete:
                    module_actions[permission.module].add("delete")
                if permission.can_approve:
                    module_actions[permission.module].add("approve")
                if permission.can_export:
                    module_actions[permission.module].add("export")
                if permission.can_print:
                    module_actions[permission.module].add("print")
                if permission.can_manage:
                    module_actions[permission.module].add("manage")
        else:
            for group_name in user.groups.values_list("name", flat=True):
                preset = default_permissions_for_role(group_name)
                for module_name, actions in preset.items():
                    if actions:
                        module_actions[module_name].update(actions)
                        module_access[f"{module_name}_access"] = True

    return {
        "user_id": user.pk,
        "module_access": module_access,
        "module_actions": {module: sorted(actions) for module, actions in module_actions.items()},
    }


def store_permission_snapshot(request, user):
    snapshot = build_permission_snapshot(user)
    if request is None:
        return snapshot
    setattr(request, PERMISSION_SNAPSHOT_REQUEST_ATTR, snapshot)
    if hasattr(request, "session"):
        request.session.pop(PERMISSION_SNAPSHOT_SESSION_KEY, None)
        request.session.modified = True
    return snapshot


def clear_permission_snapshot(request):
    if request is None:
        return
    if hasattr(request, PERMISSION_SNAPSHOT_REQUEST_ATTR):
        delattr(request, PERMISSION_SNAPSHOT_REQUEST_ATTR)
    if hasattr(request, "session"):
        request.session.pop(PERMISSION_SNAPSHOT_SESSION_KEY, None)
        request.session.modified = True


def get_permission_snapshot(user):
    from accounts.audit import get_current_request

    request = get_current_request()
    if request is None:
        return None
    snapshot = getattr(request, PERMISSION_SNAPSHOT_REQUEST_ATTR, None)
    if not snapshot or snapshot.get("user_id") != getattr(user, "pk", None):
        return None
    return snapshot


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

    snapshot = get_permission_snapshot(user)
    if snapshot is None:
        snapshot = build_permission_snapshot(user)
        from accounts.audit import get_current_request

        request = get_current_request()
        if request is not None:
            setattr(request, PERMISSION_SNAPSHOT_REQUEST_ATTR, snapshot)
            if hasattr(request, "session"):
                request.session.pop(PERMISSION_SNAPSHOT_SESSION_KEY, None)
                request.session.modified = True

    module_access = snapshot.get("module_access", {})
    module_actions = snapshot.get("module_actions", {})
    action_set = set(module_actions.get(module_name, []))

    if action == "view":
        return bool(module_access.get(MODULE_FIELDS.get(module_name, ""), False) or "view" in action_set)
    return action in action_set


def user_is_admin_role(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user.groups.filter(name__in=ADMIN_ROLE_NAMES).exists()


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
