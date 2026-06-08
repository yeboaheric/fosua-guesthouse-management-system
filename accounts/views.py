import csv
import json
from datetime import date, timedelta
from calendar import monthrange
from itertools import chain
from urllib.parse import quote_plus, unquote_plus

from django.contrib import messages
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db import IntegrityError, transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.deletion import ProtectedError
from django.db.models.functions import Coalesce
from django.db.models.functions import TruncDate
from django.http import HttpResponse, QueryDict
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.audit import log_audit_event
from accounts.decorators import group_required
from accounts.forms import (
    AttendanceRecordForm,
    DisciplinaryRecordForm,
    EmployeeDocumentForm,
    EmployeeForm,
    EmployeeQualificationForm,
    EmploymentHistoryForm,
    LeaveRequestForm,
    PayrollRecordForm,
    PerformanceReviewForm,
    RoleCreateForm,
    RolePermissionForm,
    RotaForm,
    StaffRoleForm,
    StaffUserForm,
    TrainingRecordForm,
)
from accounts.models import (
    AttendanceRecord,
    AuditLog,
    DisciplinaryRecord,
    Employee,
    EmployeeDocument,
    EmployeeQualification,
    EmploymentHistoryEntry,
    LeaveRequest,
    PayrollRecord,
    PerformanceReview,
    Rota,
    RolePermission,
    LEAVE_TYPE_TO_EMPLOYMENT_STATUS,
    TrainingRecord,
    Notification,
    StatusHistory,
)
from accounts.permissions import (
    ACTION_CHOICES,
    ACCESS_MODULE_CHOICES,
    default_permissions_for_role,
    seed_default_role_names,
    user_has_permission,
)
from bookings.models import Booking, EventBooking, Payment
from bookings.models import EventPayment
from guests.models import Guest
from inventory.models import InventoryItem, Sale
from rooms.models import Room


class FosuaLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class FosuaLogoutView(LogoutView):
    pass


def home_redirect(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("login")


def _is_group_member(user, group_name):
    return user.groups.filter(name=group_name).exists()


def _user_can_access_module(user, module_name):
    return user_has_permission(user, module_name, "view")


def _permission_defaults_from_actions(actions):
    return {
        "can_view": "view" in actions,
        "can_create": "create" in actions,
        "can_edit": "edit" in actions,
        "can_delete": "delete" in actions,
        "can_approve": "approve" in actions,
        "can_export": "export" in actions,
        "can_print": "print" in actions,
        "can_manage": "manage" in actions,
    }


def _seed_default_roles():
    role_names = set(seed_default_role_names()) | {"Admin"}
    for role_name in role_names:
        role, _ = Group.objects.get_or_create(name=role_name)
        if role.role_permissions.exists():
            continue
        if role.name == "Admin":
            preset = {module: {action for action, _ in ACTION_CHOICES} for module, _ in ACCESS_MODULE_CHOICES}
        else:
            preset = default_permissions_for_role(role.name)
        for module_name, actions in preset.items():
            RolePermission.objects.update_or_create(
                role=role,
                module=module_name,
                defaults=_permission_defaults_from_actions(actions),
            )


def _dashboard_snapshot(user=None):
    today = timezone.localdate()
    now = timezone.localtime()
    month_start = today.replace(day=1)

    total_rooms = Room.objects.count()
    available_rooms = Room.objects.filter(status=Room.RoomStatus.AVAILABLE).count()
    occupied_rooms = Room.objects.filter(status=Room.RoomStatus.OCCUPIED).count()
    cleaning_rooms = Room.objects.filter(status=Room.RoomStatus.CLEANING).count()
    maintenance_rooms = Room.objects.filter(status=Room.RoomStatus.MAINTENANCE).count()
    active_bookings = Booking.objects.filter(
        status__in=[
            Booking.BookingStatus.PENDING,
            Booking.BookingStatus.CONFIRMED,
            Booking.BookingStatus.CHECKED_IN,
        ]
    ).count()
    total_guests = Guest.objects.count()
    staff_on_duty = Rota.objects.filter(
        period_start__lte=today,
        period_end__gte=today,
        employee__employment_status="active",
    ).count()

    room_revenue_today = Payment.objects.filter(paid_at__date=today).aggregate(
        total=Coalesce(
            Sum("amount"),
            Value(0, output_field=DecimalField(max_digits=10, decimal_places=2)),
        )
    )["total"]
    event_revenue_today = EventPayment.objects.filter(paid_at__date=today).aggregate(
        total=Coalesce(
            Sum("amount"),
            Value(0, output_field=DecimalField(max_digits=10, decimal_places=2)),
        )
    )["total"]

    room_revenue_month = Payment.objects.filter(paid_at__date__gte=month_start).aggregate(
        total=Coalesce(
            Sum("amount"),
            Value(0, output_field=DecimalField(max_digits=10, decimal_places=2)),
        )
    )["total"]
    event_revenue_month = EventPayment.objects.filter(paid_at__date__gte=month_start).aggregate(
        total=Coalesce(
            Sum("amount"),
            Value(0, output_field=DecimalField(max_digits=10, decimal_places=2)),
        )
    )["total"]

    bookings_with_balance = Booking.objects.annotate(
        paid_total=Coalesce(
            Sum("payments__amount"),
            Value(0, output_field=DecimalField(max_digits=10, decimal_places=2)),
        ),
        balance=ExpressionWrapper(
            F("total_amount") - F("paid_total"),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
    )
    pending_room_balances = bookings_with_balance.filter(balance__gt=0).count()

    event_bookings_with_balance = EventBooking.objects.annotate(
        paid_total=Coalesce(
            Sum("payments__amount"),
            Value(0, output_field=DecimalField(max_digits=10, decimal_places=2)),
        ),
        balance=ExpressionWrapper(
            F("total_amount") - F("paid_total"),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
    )
    pending_event_balances = event_bookings_with_balance.filter(balance__gt=0).count()

    occupancy_rate = round((occupied_rooms / total_rooms) * 100, 1) if total_rooms else 0
    last_7_rows = _daily_report_rows(today - timedelta(days=6), today, total_rooms or 1)

    upcoming_window = now + timedelta(hours=1)
    today_check_ins = Booking.objects.filter(
        check_in=today,
        status__in=[
            Booking.BookingStatus.PENDING,
            Booking.BookingStatus.CONFIRMED,
        ],
    )
    today_check_outs = Booking.objects.filter(
        check_out=today,
        status__in=[
            Booking.BookingStatus.CHECKED_IN,
            Booking.BookingStatus.CONFIRMED,
        ],
    )
    upcoming_check_ins = Booking.objects.filter(
        check_in=today,
        check_in_time__gte=now.time(),
        check_in_time__lte=upcoming_window.time(),
        status__in=[
            Booking.BookingStatus.PENDING,
            Booking.BookingStatus.CONFIRMED,
        ],
    )
    upcoming_check_outs = Booking.objects.filter(
        check_out=today,
        check_out_time__gte=now.time(),
        check_out_time__lte=upcoming_window.time(),
        status__in=[Booking.BookingStatus.CHECKED_IN],
    )
    reserved_rooms = Booking.objects.filter(status=Booking.BookingStatus.CONFIRMED).count()

    snapshot = {
        "today": today,
        "month_start": month_start,
        "total_rooms": total_rooms,
        "available_rooms": available_rooms,
        "occupied_rooms": occupied_rooms,
        "cleaning_rooms": cleaning_rooms,
        "maintenance_rooms": maintenance_rooms,
        "active_bookings": active_bookings,
        "total_guests": total_guests,
        "staff_on_duty": staff_on_duty,
        "room_revenue_today": room_revenue_today,
        "event_revenue_today": event_revenue_today,
        "daily_revenue": room_revenue_today + event_revenue_today,
        "room_revenue_month": room_revenue_month,
        "event_revenue_month": event_revenue_month,
        "monthly_revenue": room_revenue_month + event_revenue_month,
        "pending_room_balances": pending_room_balances,
        "pending_event_balances": pending_event_balances,
        "pending_payments": pending_room_balances + pending_event_balances,
        "occupancy_rate": occupancy_rate,
        "reserved_rooms": reserved_rooms,
        "today_check_ins": today_check_ins,
        "today_check_outs": today_check_outs,
        "upcoming_check_ins": upcoming_check_ins,
        "upcoming_check_outs": upcoming_check_outs,
        "room_status_breakdown": [
            {"label": "Available", "count": available_rooms, "tone": "success"},
            {"label": "Occupied", "count": occupied_rooms, "tone": "primary"},
            {"label": "Cleaning", "count": cleaning_rooms, "tone": "warning"},
            {"label": "Maintenance", "count": maintenance_rooms, "tone": "danger"},
        ],
        "recent_activity": _recent_activity_feed(),
        "recent_bookings": Booking.objects.select_related("guest", "room").order_by("-created_at")[:6],
        "recent_payments": Payment.objects.select_related("booking__guest", "booking__room", "received_by").order_by("-paid_at")[:6],
        "recent_event_bookings": EventBooking.objects.select_related("guest").order_by("-created_at")[:6],
        "chart_labels_json": json.dumps([row["date"] for row in last_7_rows]),
        "revenue_data_json": json.dumps([float(row["revenue_collected"]) for row in last_7_rows]),
        "occupancy_data_json": json.dumps([row["occupied_rooms"] for row in last_7_rows]),
    }

    if user and _user_can_access_module(user, "notifications"):
        _generate_booking_reminder_notifications(user)
        snapshot["unread_notifications_count"] = Notification.objects.filter(
            user=user,
            read_at__isnull=True,
        ).count()
    else:
        snapshot["unread_notifications_count"] = 0

    return snapshot


def _generate_booking_reminder_notifications(user):
    if not user:
        return

    now = timezone.localtime()
    upcoming_window = now + timedelta(hours=1)
    today = now.date()

    check_ins = Booking.objects.filter(
        check_in=today,
        check_in_time__gte=now.time(),
        check_in_time__lte=upcoming_window.time(),
        status__in=[Booking.BookingStatus.PENDING, Booking.BookingStatus.CONFIRMED],
    )
    check_outs = Booking.objects.filter(
        check_out=today,
        check_out_time__gte=now.time(),
        check_out_time__lte=upcoming_window.time(),
        status__in=[Booking.BookingStatus.CHECKED_IN],
    )

    for booking in check_ins:
        title = f"Upcoming check-in for {booking.guest} in Room {booking.room.room_number}"
        if Notification.objects.filter(user=user, title=title).exists():
            continue
        Notification.objects.create(
            user=user,
            title=title,
            message=(
                f"Room {booking.room.room_number} is due at "
                f"{booking.check_in_time.strftime('%H:%M')} on {booking.check_in}."
            ),
            link=reverse("booking-detail", args=[booking.pk]),
            level=Notification.Level.INFO,
        )

    for booking in check_outs:
        title = f"Upcoming check-out for {booking.guest} in Room {booking.room.room_number}"
        if Notification.objects.filter(user=user, title=title).exists():
            continue
        Notification.objects.create(
            user=user,
            title=title,
            message=(
                f"Room {booking.room.room_number} is due for check-out at "
                f"{booking.check_out_time.strftime('%H:%M')} on {booking.check_out}."
            ),
            link=reverse("booking-detail", args=[booking.pk]),
            level=Notification.Level.WARNING,
        )


@login_required
def dashboard(request):
    if request.user.is_superuser or _is_group_member(request.user, "Admin"):
        return redirect("admin-dashboard")

    if _is_group_member(request.user, "Receptionist"):
        return redirect("reception-dashboard")

    return render(request, "accounts/dashboard.html")


@group_required("Admin")
def admin_dashboard(request):
    context = _dashboard_snapshot(user=request.user)
    context["role_label"] = "Admin"
    return render(request, "accounts/admin_dashboard.html", context)


@group_required("Receptionist", "Admin", module="dashboard")
def reception_dashboard(request):
    context = _dashboard_snapshot(user=request.user)
    context["role_label"] = "Reception"
    return render(request, "accounts/reception_dashboard.html", context)


@login_required
def global_search(request):
    query = request.GET.get("q", "").strip()
    context = {"query": query}
    if not query:
        return render(request, "accounts/global_search.html", context)

    user = request.user
    context.update(
        {
            "guest_results": Guest.objects.filter(
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(phone_number__icontains=query)
                | Q(email__icontains=query)
                | Q(ghana_card_number__icontains=query)
            ).order_by("last_name", "first_name")[:8]
            if _user_can_access_module(user, "guests")
            else [],
            "room_results": Room.objects.filter(
                Q(room_number__icontains=query)
                | Q(notes__icontains=query)
                | Q(room_type__icontains=query)
            ).order_by("room_number")[:8]
            if _user_can_access_module(user, "rooms")
            else [],
            "booking_results": Booking.objects.select_related("guest", "room").filter(
                Q(guest__first_name__icontains=query)
                | Q(guest__last_name__icontains=query)
                | Q(room__room_number__icontains=query)
                | Q(status__icontains=query)
            ).order_by("-created_at")[:8]
            if _user_can_access_module(user, "reservations")
            else [],
            "inventory_results": InventoryItem.objects.select_related("category", "subcategory", "supplier").filter(
                Q(name__icontains=query)
                | Q(category__name__icontains=query)
                | Q(subcategory__name__icontains=query)
                | Q(supplier__name__icontains=query)
            ).order_by("name")[:8]
            if _user_can_access_module(user, "inventory")
            else [],
            "sale_results": Sale.objects.select_related("cashier").filter(
                Q(receipt_number__icontains=query)
                | Q(customer_name__icontains=query)
                | Q(customer_phone__icontains=query)
                | Q(customer_email__icontains=query)
            ).order_by("-created_at")[:8]
            if _user_can_access_module(user, "pos")
            else [],
            "payment_results": Payment.objects.select_related("booking__guest", "booking__room").filter(
                Q(reference__icontains=query)
                | Q(notes__icontains=query)
                | Q(booking__guest__first_name__icontains=query)
                | Q(booking__guest__last_name__icontains=query)
                | Q(booking__room__room_number__icontains=query)
            ).order_by("-paid_at")[:8]
            if _user_can_access_module(user, "payments")
            else [],
            "employee_results": Employee.objects.filter(
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(position__icontains=query)
                | Q(ghana_card_number__icontains=query)
            ).order_by("last_name", "first_name")[:8]
            if _user_can_access_module(user, "staff_management")
            else [],
            "event_results": EventBooking.objects.select_related("guest").filter(
                Q(event_title__icontains=query)
                | Q(event_space_name__icontains=query)
                | Q(guest__first_name__icontains=query)
                | Q(guest__last_name__icontains=query)
            ).order_by("-created_at")[:8]
            if _user_can_access_module(user, "services")
            else [],
            "event_payment_results": EventPayment.objects.select_related(
                "event_booking__guest"
            ).filter(
                Q(reference__icontains=query)
                | Q(notes__icontains=query)
                | Q(event_booking__event_title__icontains=query)
                | Q(event_booking__guest__first_name__icontains=query)
                | Q(event_booking__guest__last_name__icontains=query)
            ).order_by("-paid_at")[:8]
            if _user_can_access_module(user, "payments")
            else [],
        }
    )
    return render(request, "accounts/global_search.html", context)


@group_required("Admin", "Receptionist", module="payments")
def payments_center(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)
    query = request.GET.get("q", "").strip()
    payment_method = request.GET.get("method", "")
    payment_scope = request.GET.get("scope", "all")

    room_payments = Payment.objects.select_related("booking__guest", "booking__room", "received_by").order_by("-paid_at")
    event_payments = EventPayment.objects.select_related("event_booking__guest", "received_by").order_by("-paid_at")

    if query:
        room_payments = room_payments.filter(
            Q(reference__icontains=query)
            | Q(notes__icontains=query)
            | Q(booking__guest__first_name__icontains=query)
            | Q(booking__guest__last_name__icontains=query)
            | Q(booking__room__room_number__icontains=query)
        )
        event_payments = event_payments.filter(
            Q(reference__icontains=query)
            | Q(notes__icontains=query)
            | Q(event_booking__event_title__icontains=query)
            | Q(event_booking__guest__first_name__icontains=query)
            | Q(event_booking__guest__last_name__icontains=query)
            | Q(event_booking__event_space_name__icontains=query)
        )

    if payment_method:
        room_payments = room_payments.filter(method=payment_method)
        event_payments = event_payments.filter(method=payment_method)

    if payment_scope == "room":
        event_payments = event_payments.none()
    elif payment_scope == "event":
        room_payments = room_payments.none()

    room_payments = room_payments[:20]
    event_payments = event_payments[:20]

    context = {
        "today_total": Payment.objects.filter(paid_at__date=today).aggregate(
            total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField(max_digits=10, decimal_places=2)))
        )["total"]
        + EventPayment.objects.filter(paid_at__date=today).aggregate(
            total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField(max_digits=10, decimal_places=2)))
        )["total"],
        "month_total": Payment.objects.filter(paid_at__date__gte=month_start).aggregate(
            total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField(max_digits=10, decimal_places=2)))
        )["total"]
        + EventPayment.objects.filter(paid_at__date__gte=month_start).aggregate(
            total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField(max_digits=10, decimal_places=2)))
        )["total"],
        "room_payments": room_payments,
        "event_payments": event_payments,
        "query": query,
        "payment_method": payment_method,
        "payment_scope": payment_scope,
        "payment_methods": Payment.PaymentMethod.choices,
    }
    return render(request, "accounts/payments_center.html", context)


@group_required("Admin", "Receptionist", module="services")
def services_center(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    events = EventBooking.objects.select_related("guest").order_by("-created_at")

    if query:
        events = events.filter(
            Q(event_title__icontains=query)
            | Q(event_space_name__icontains=query)
            | Q(purpose__icontains=query)
            | Q(guest__first_name__icontains=query)
            | Q(guest__last_name__icontains=query)
        )
    if status:
        events = events.filter(status=status)

    return render(
        request,
        "accounts/services_center.html",
        {
            "events": events[:12],
            "query": query,
            "selected_status": status,
            "status_choices": EventBooking.EventBookingStatus.choices,
        },
    )


@group_required("Admin", "Receptionist", module="housekeeping")
def housekeeping_center(request):
    report_range = request.GET.get("report", "daily")
    return redirect(f"{reverse('housekeeping-dashboard')}?report={report_range}")


@group_required("Admin", "Receptionist", module="notifications")
def notifications_center(request):
    _generate_booking_reminder_notifications(request.user)
    notifications = Notification.objects.filter(user=request.user).order_by("-created_at")
    unread_count = notifications.filter(read_at__isnull=True).count()
    return render(
        request,
        "accounts/notifications_center.html",
        {
            "notifications": notifications,
            "unread_count": unread_count,
        },
    )


@group_required("Admin", "Receptionist", module="notifications")
def notification_mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])
        messages.success(request, "Notification marked read.")
    return redirect("notifications-center")


@group_required("Admin")
def settings_center(request):
    return render(
        request,
        "accounts/settings_center.html",
        {
            "room_categories": [
                {"label": "Deluxe", "count": Room.objects.filter(room_type=Room.RoomType.DELUXE).count()},
                {"label": "Standard", "count": Room.objects.filter(room_type=Room.RoomType.STANDARD).count()},
            ],
            "payment_methods": ["Cash", "Mobile Money", "Card", "Bank Transfer"],
        },
    )


@group_required("Admin", "Super Administrator", module="users_roles")
def users_roles_center(request):
    _seed_default_roles()

    users = User.objects.select_related("staff_profile", "access_profile").prefetch_related("groups", "groups__role_permissions").order_by("username")
    roles = Group.objects.prefetch_related("role_permissions").order_by("name")
    create_form = StaffUserForm()
    role_create_form = RoleCreateForm()
    user_forms = {user.pk: StaffRoleForm(user=user, initial={"user_id": user.pk}) for user in users}
    role_permission_forms = {role.pk: RolePermissionForm(role=role, initial={"role_id": role.pk}) for role in roles}

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create_user":
            create_form = StaffUserForm(request.POST, request.FILES)
            if create_form.is_valid():
                user = create_form.save()
                log_audit_event(
                    request=request,
                    user=request.user,
                    action=AuditLog.ActionType.CREATE,
                    module="users_roles",
                    object_repr=user.username,
                    object_id=user.pk,
                    details={
                        "event": "user_created",
                        "roles": list(user.groups.values_list("name", flat=True)),
                    },
                )
                messages.success(request, f"User '{user.username}' created successfully.")
                return redirect("users-roles-center")
        elif action == "update_user":
            user = get_object_or_404(User, pk=request.POST.get("user_id"))
            role_form = StaffRoleForm(request.POST, request.FILES, user=user)
            user_forms[user.pk] = role_form
            if role_form.is_valid():
                updated_user = role_form.save()
                log_audit_event(
                    request=request,
                    user=request.user,
                    action=AuditLog.ActionType.UPDATE,
                    module="users_roles",
                    object_repr=updated_user.username,
                    object_id=updated_user.pk,
                    details={
                        "event": "user_updated",
                        "roles": list(updated_user.groups.values_list("name", flat=True)),
                        "is_active": updated_user.is_active,
                        "is_staff": updated_user.is_staff,
                    },
                )
                messages.success(request, f"Roles updated for '{user.username}'.")
                return redirect("users-roles-center")
        elif action == "delete_user":
            user = get_object_or_404(User, pk=request.POST.get("user_id"))
            if user.pk == request.user.pk:
                messages.error(request, "You cannot delete your own account while logged in.")
            else:
                username = user.username
                user_id = user.pk
                try:
                    with transaction.atomic():
                        user.delete()
                except ProtectedError:
                    messages.error(request, f"User '{username}' could not be deleted because the account is linked to other records.")
                except IntegrityError:
                    messages.error(request, f"User '{username}' could not be deleted because the database rejected the operation.")
                else:
                    try:
                        log_audit_event(
                            request=request,
                            user=request.user,
                            action=AuditLog.ActionType.DELETE,
                            module="users_roles",
                            object_repr=username,
                            object_id=user_id,
                            details={"event": "user_deleted"},
                        )
                    except Exception:
                        pass
                    messages.success(request, f"User '{username}' deleted successfully.")
                    return redirect("users-roles-center")
        elif action == "create_role":
            role_create_form = RoleCreateForm(request.POST)
            if role_create_form.is_valid():
                role = role_create_form.save()
                log_audit_event(
                    request=request,
                    user=request.user,
                    action=AuditLog.ActionType.CREATE,
                    module="users_roles",
                    object_repr=role.name,
                    object_id=role.pk,
                    details={"event": "role_created"},
                )
                messages.success(request, f"Role '{role.name}' created successfully.")
                return redirect("users-roles-center")
        elif action == "save_role_permissions":
            role = get_object_or_404(Group, pk=request.POST.get("role_id"))
            role_form = RolePermissionForm(request.POST, role=role)
            role_permission_forms[role.pk] = role_form
            if role_form.is_valid():
                role = role_form.save()
                log_audit_event(
                    request=request,
                    user=request.user,
                    action=AuditLog.ActionType.PERMISSION_CHANGE,
                    module="users_roles",
                    object_repr=role.name,
                    object_id=role.pk,
                    details={"event": "role_permissions_updated"},
                )
                messages.success(request, f"Permissions updated for role '{role.name}'.")
                return redirect("users-roles-center")

    recent_audit_logs = AuditLog.objects.select_related("user").order_by("-created_at")[:15]
    return render(
        request,
        "accounts/users_roles_center.html",
        {
            "create_form": create_form,
            "role_create_form": role_create_form,
            "users": users,
            "role_forms": user_forms,
            "role_permission_forms": role_permission_forms,
            "available_roles": roles,
            "recent_audit_logs": recent_audit_logs,
            "permission_modules": ACCESS_MODULE_CHOICES,
            "permission_actions": ACTION_CHOICES,
        },
    )


@group_required("Admin", "Receptionist", module="analytics")
def analytics_center(request):
    start_date, end_date = _parse_report_range(request)
    total_rooms = Room.objects.count()
    daily_rows = _daily_report_rows(start_date, end_date, total_rooms)
    period_revenue_total = sum((row["revenue_collected"] for row in daily_rows), 0)
    return render(
        request,
        "accounts/analytics_center.html",
        {
            "start_date": start_date,
            "end_date": end_date,
            "daily_rows": daily_rows,
            "period_revenue_total": period_revenue_total,
            "active_bookings": Booking.objects.filter(
                status__in=[
                    Booking.BookingStatus.PENDING,
                    Booking.BookingStatus.CONFIRMED,
                    Booking.BookingStatus.CHECKED_IN,
                ]
            ).count(),
            "chart_labels_json": json.dumps([row["date"] for row in daily_rows]),
            "revenue_data_json": json.dumps([float(row["revenue_collected"]) for row in daily_rows]),
            "occupancy_data_json": json.dumps([row["occupied_rooms"] for row in daily_rows]),
        },
    )


STAFF_FILTER_QUERY_KEYS = (
    "staff_view",
    "q",
    "department",
    "status",
    "role",
    "certifications",
    "roster",
)

LEAVE_EMPLOYMENT_STATUSES = tuple(dict(LEAVE_TYPE_TO_EMPLOYMENT_STATUS).values())
EMPLOYMENT_STATUS_TO_LEAVE_TYPE = {
    employment_status: leave_type
    for leave_type, employment_status in LEAVE_TYPE_TO_EMPLOYMENT_STATUS.items()
}


def _build_staff_filters_token(params):
    query = QueryDict("", mutable=True)
    staff_view = (params.get("staff_view", "").strip() or "active")
    if staff_view not in {"active", "terminated"}:
        staff_view = "active"

    for key in STAFF_FILTER_QUERY_KEYS:
        value = params.get(key, "").strip()
        if value and (key != "staff_view" or value != "active"):
            query[key] = value

    encoded = query.urlencode()
    return quote_plus(encoded) if encoded else ""


def _decode_staff_filters_token(token):
    if not token:
        return "", QueryDict("", mutable=False)
    query_string = unquote_plus(token).strip()
    return query_string, QueryDict(query_string, mutable=False)


def _append_query_param(url, name, value):
    if not value:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{name}={value}"


def _current_leave_q():
    today = timezone.localdate()
    return Q(
        leave_requests__approval_status=LeaveRequest.ApprovalStatus.APPROVED,
        leave_requests__start_date__lte=today,
        leave_requests__end_date__gte=today,
    )


def _system_status_filter_options():
    status_labels = dict(Employee.EMPLOYMENT_STATUS_CHOICES)
    options = [("active", "Active"), ("terminated", "Terminated")]
    options.extend(
        (employment_status, dict(LeaveRequest.LeaveType.choices).get(leave_type, status_labels.get(employment_status)))
        for leave_type, employment_status in LEAVE_TYPE_TO_EMPLOYMENT_STATUS.items()
    )

    existing_values = {value for value, _label in options}
    available_statuses = sorted(
        set(
            Employee.objects.exclude(employment_status="")
            .values_list("employment_status", flat=True)
            .distinct()
        )
    )
    for value in available_statuses:
        if value in existing_values:
            continue
        options.append((value, status_labels.get(value, value.replace("_", " ").title())))
    return options


def _system_role_filter_options():
    position_labels = dict(Employee.POSITION_CHOICES)
    positions = sorted(
        set(
            Employee.objects.exclude(position="")
            .values_list("position", flat=True)
            .distinct()
        )
    )
    return [
        (value, position_labels.get(value, value.replace("_", " ").title()))
        for value in positions
    ]


def _system_certification_filter_options():
    options = []
    qualification_names = sorted(
        set(
            EmployeeQualification.objects.exclude(qualification_name="")
            .values_list("qualification_name", flat=True)
            .distinct()
        )
    )
    if EmployeeQualification.objects.exists():
        options.extend(
            [
                ("expiring", "Expiring Soon"),
                ("expired", "Expired"),
            ]
        )
    options.extend((name, name) for name in qualification_names)
    return options


def _system_roster_filter_options():
    rotas = (
        Rota.objects.select_related("employee")
        .prefetch_related("staff_members")
        .filter(Q(employee__isnull=False) | Q(staff_members__isnull=False))
        .order_by("-period_start", "-created_at")
        .distinct()
    )
    options = []
    for rota in rotas:
        assigned_names = []
        if rota.employee_id:
            assigned_names.append(rota.employee.full_name)
        for member in rota.staff_members.all():
            if member.full_name not in assigned_names:
                assigned_names.append(member.full_name)
        label_parts = [
            rota.period or f"{rota.period_start or '-'} to {rota.period_end or '-'}",
        ]
        if rota.operating_hours != "-":
            label_parts.append(rota.operating_hours)
        if assigned_names:
            label_parts.append(", ".join(assigned_names))
        options.append((f"rota:{rota.pk}", " · ".join(label_parts)))
    return options


def _employee_section_filters(section, params):
    filters = []

    def add_select(name, label, choices):
        filters.append(
            {
                "name": name,
                "label": label,
                "type": "select",
                "choices": [("", "All")] + list(choices),
                "value": params.get(name, "").strip(),
            }
        )

    def add_date(name, label):
        filters.append(
            {
                "name": name,
                "label": label,
                "type": "date",
                "value": params.get(name, "").strip(),
            }
        )

    def add_text(name, label, placeholder):
        filters.append(
            {
                "name": name,
                "label": label,
                "type": "text",
                "placeholder": placeholder,
                "value": params.get(name, "").strip(),
            }
        )

    if section == "leave":
        add_select("approval_status", "Status", LeaveRequest.ApprovalStatus.choices)
        add_select("leave_type", "Leave Type", LeaveRequest.LeaveType.choices)
        add_date("date_from", "Start From")
        add_date("date_to", "End To")
    elif section == "attendance":
        add_select("attendance_status", "Status", AttendanceRecord.AttendanceStatus.choices)
        add_date("date_from", "Date From")
        add_date("date_to", "Date To")
    elif section == "certifications":
        add_select(
            "certification_status",
            "Status",
            [
                ("current", "Current"),
                ("expiring", "Expiring Soon"),
                ("expired", "Expired"),
            ],
        )
        add_text("query", "Search", "Qualification or institution")
        add_date("date_from", "Issued From")
        add_date("date_to", "Issued To")
    elif section == "documents":
        add_select("document_type", "Type", EmployeeDocument.DocumentType.choices)
        add_text("query", "Search", "Title or description")
    elif section == "payroll":
        add_select("payment_status", "Status", PayrollRecord.PaymentStatus.choices)
        add_date("date_from", "Period From")
        add_date("date_to", "Period To")
    elif section == "performance":
        add_select(
            "rating",
            "Rating",
            [(str(value), str(value)) for value in range(1, 6)],
        )
        add_date("date_from", "Review From")
        add_date("date_to", "Review To")
    elif section == "disciplinary":
        add_select("record_type", "Type", DisciplinaryRecord.RecordType.choices)
        add_select(
            "resolved",
            "Resolved",
            [("yes", "Yes"), ("no", "No")],
        )
        add_date("date_from", "Incident From")
        add_date("date_to", "Incident To")
    elif section == "training":
        add_text("query", "Search", "Training or provider")
        add_date("date_from", "Completed From")
        add_date("date_to", "Completed To")
    elif section == "history":
        add_select("change_type", "Change Type", EmploymentHistoryEntry.ChangeType.choices)
        add_date("date_from", "Effective From")
        add_date("date_to", "Effective To")

    return filters


def _apply_employee_section_filters(records, section, params):
    if section == "leave":
        approval_status = params.get("approval_status", "").strip()
        leave_type = params.get("leave_type", "").strip()
        date_from = params.get("date_from", "").strip()
        date_to = params.get("date_to", "").strip()
        if approval_status:
            records = records.filter(approval_status=approval_status)
        if leave_type:
            records = records.filter(leave_type=leave_type)
        if date_from:
            records = records.filter(start_date__gte=date_from)
        if date_to:
            records = records.filter(end_date__lte=date_to)
        return records

    if section == "attendance":
        attendance_status = params.get("attendance_status", "").strip()
        date_from = params.get("date_from", "").strip()
        date_to = params.get("date_to", "").strip()
        if attendance_status:
            records = records.filter(status=attendance_status)
        if date_from:
            records = records.filter(work_date__gte=date_from)
        if date_to:
            records = records.filter(work_date__lte=date_to)
        return records

    if section == "certifications":
        certification_status = params.get("certification_status", "").strip()
        query = params.get("query", "").strip()
        date_from = params.get("date_from", "").strip()
        date_to = params.get("date_to", "").strip()
        today = timezone.localdate()
        if certification_status == "current":
            records = records.filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=today))
        elif certification_status == "expiring":
            records = records.filter(
                expiry_date__isnull=False,
                expiry_date__gte=today,
                expiry_date__lte=today + timedelta(days=30),
            )
        elif certification_status == "expired":
            records = records.filter(expiry_date__isnull=False, expiry_date__lt=today)
        if query:
            records = records.filter(
                Q(qualification_name__icontains=query)
                | Q(institution__icontains=query)
                | Q(certificate_number__icontains=query)
            )
        if date_from:
            records = records.filter(certification_date__gte=date_from)
        if date_to:
            records = records.filter(certification_date__lte=date_to)
        return records

    if section == "documents":
        document_type = params.get("document_type", "").strip()
        query = params.get("query", "").strip()
        if document_type:
            records = records.filter(document_type=document_type)
        if query:
            records = records.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )
        return records

    if section == "payroll":
        payment_status = params.get("payment_status", "").strip()
        date_from = params.get("date_from", "").strip()
        date_to = params.get("date_to", "").strip()
        if payment_status:
            records = records.filter(payment_status=payment_status)
        if date_from:
            records = records.filter(pay_period_start__gte=date_from)
        if date_to:
            records = records.filter(pay_period_end__lte=date_to)
        return records

    if section == "performance":
        rating = params.get("rating", "").strip()
        date_from = params.get("date_from", "").strip()
        date_to = params.get("date_to", "").strip()
        if rating:
            records = records.filter(rating=rating)
        if date_from:
            records = records.filter(review_date__gte=date_from)
        if date_to:
            records = records.filter(review_date__lte=date_to)
        return records

    if section == "disciplinary":
        record_type = params.get("record_type", "").strip()
        resolved = params.get("resolved", "").strip()
        date_from = params.get("date_from", "").strip()
        date_to = params.get("date_to", "").strip()
        if record_type:
            records = records.filter(record_type=record_type)
        if resolved == "yes":
            records = records.filter(resolved=True)
        elif resolved == "no":
            records = records.filter(resolved=False)
        if date_from:
            records = records.filter(incident_date__gte=date_from)
        if date_to:
            records = records.filter(incident_date__lte=date_to)
        return records

    if section == "training":
        query = params.get("query", "").strip()
        date_from = params.get("date_from", "").strip()
        date_to = params.get("date_to", "").strip()
        if query:
            records = records.filter(
                Q(training_name__icontains=query) | Q(provider__icontains=query)
            )
        if date_from:
            records = records.filter(completion_date__gte=date_from)
        if date_to:
            records = records.filter(completion_date__lte=date_to)
        return records

    if section == "history":
        change_type = params.get("change_type", "").strip()
        date_from = params.get("date_from", "").strip()
        date_to = params.get("date_to", "").strip()
        if change_type:
            records = records.filter(change_type=change_type)
        if date_from:
            records = records.filter(effective_date__gte=date_from)
        if date_to:
            records = records.filter(effective_date__lte=date_to)
        return records

    return records


def _employee_section_links(employee, staff_filters_token="", active_section=None):
    section_specs = [
        ("leave", "Annual Leave", employee.leave_requests.count()),
        ("certifications", "Certifications", employee.qualifications.count()),
        ("documents", "Documents", employee.documents.count()),
        ("attendance", "Attendance History", employee.attendance_records.count()),
        ("payroll", "Payroll Information", employee.payroll_records.count()),
        ("performance", "Performance Reviews", employee.performance_reviews.count()),
        ("disciplinary", "Disciplinary Records", employee.disciplinary_records.count()),
        ("training", "Training Records", employee.training_records.count()),
        ("history", "Employment History", employee.history_entries.count()),
    ]
    links = []
    for key, label, count in section_specs:
        url = reverse("hr-employee-section", args=[employee.pk, key])
        url = _append_query_param(url, "staff_filters", staff_filters_token)
        links.append(
            {
                "key": key,
                "label": label,
                "count": count,
                "url": url,
                "active": key == active_section,
            }
        )

    roster_url = reverse("hr-rota-list")
    roster_url = _append_query_param(roster_url, "employee", employee.pk)
    links.append(
        {
            "key": "roster",
            "label": "Roster Assignments",
            "count": employee.rota_entries.count(),
            "url": roster_url,
            "active": active_section == "roster",
        }
    )
    return links


def _employee_section_headers(section):
    return {
        "leave": ["Type", "Dates", "Days", "Return", "Status", "Manager"],
        "certifications": ["Qualification", "Institution", "Certificate #", "Issued", "Expires"],
        "documents": ["Type", "Title", "File", "Created"],
        "attendance": ["Date", "Shift", "Status", "Check-in", "Check-out"],
        "payroll": ["Pay period", "Gross", "Net", "Status", "Paid at"],
        "performance": ["Review date", "Reviewer", "Rating", "Next review", "Summary"],
        "disciplinary": ["Date", "Type", "Resolved", "Action taken", "Notes"],
        "training": ["Training", "Provider", "Completed", "Expires", "Notes"],
        "history": ["Change", "Effective date", "Description", "Created by"],
    }.get(section, [])


def _employee_section_records(employee, section):
    if section == "leave":
        return employee.leave_requests.select_related("approving_manager").order_by("-created_at")
    if section == "certifications":
        return employee.qualifications.order_by("-certification_date")
    if section == "documents":
        return employee.documents.order_by("-created_at")
    if section == "attendance":
        return employee.attendance_records.order_by("-work_date")
    if section == "payroll":
        return employee.payroll_records.order_by("-pay_period_start")
    if section == "performance":
        return employee.performance_reviews.select_related("reviewer").order_by("-review_date")
    if section == "disciplinary":
        return employee.disciplinary_records.order_by("-incident_date")
    if section == "training":
        return employee.training_records.order_by("-completion_date")
    if section == "history":
        return employee.history_entries.select_related("created_by").order_by("-effective_date")
    return []


def _employee_section_form_class(section):
    return {
        "leave": LeaveRequestForm,
        "certifications": EmployeeQualificationForm,
        "documents": EmployeeDocumentForm,
        "attendance": AttendanceRecordForm,
        "payroll": PayrollRecordForm,
        "performance": PerformanceReviewForm,
        "disciplinary": DisciplinaryRecordForm,
        "training": TrainingRecordForm,
        "history": EmploymentHistoryForm,
    }.get(section)


def _employee_section_title(section):
    return {
        "leave": "Annual Leave",
        "certifications": "Qualifications & Certifications",
        "documents": "Employee Documents",
        "attendance": "Attendance History",
        "payroll": "Payroll Information",
        "performance": "Performance Reviews",
        "disciplinary": "Disciplinary Records",
        "training": "Training Records",
        "history": "Employment History",
    }.get(section, "Staff Management")


def _employee_section_row(record, section):
    if section == "leave":
        return [
            record.get_leave_type_display(),
            f"{record.start_date:%Y-%m-%d} to {record.end_date:%Y-%m-%d}",
            str(record.days),
            record.return_to_work_date.strftime("%d/%m/%Y") if record.return_to_work_date else "-",
            record.get_approval_status_display(),
            record.approving_manager.full_name if record.approving_manager else "-",
        ]
    if section == "certifications":
        return [
            record.qualification_name,
            record.institution,
            record.certificate_number or "-",
            record.certification_date.strftime("%d/%m/%Y"),
            record.expiry_date.strftime("%d/%m/%Y") if record.expiry_date else "-",
        ]
    if section == "documents":
        return [
            record.get_document_type_display(),
            record.title,
            record.file.name.split("/")[-1],
            record.created_at.strftime("%d/%m/%Y"),
        ]
    if section == "attendance":
        return [
            record.work_date.strftime("%d/%m/%Y"),
            record.get_shift_type_display(),
            record.get_status_display(),
            record.check_in.strftime("%d/%m/%Y %H:%M") if record.check_in else "-",
            record.check_out.strftime("%d/%m/%Y %H:%M") if record.check_out else "-",
        ]
    if section == "payroll":
        return [
            f"{record.pay_period_start:%Y-%m-%d} to {record.pay_period_end:%Y-%m-%d}",
            f"GHS {record.basic_salary}",
            f"GHS {record.net_pay}",
            record.get_payment_status_display(),
            record.paid_at.strftime("%d/%m/%Y %H:%M") if record.paid_at else "-",
        ]
    if section == "performance":
        return [
            record.review_date.strftime("%d/%m/%Y"),
            record.reviewer.get_username() if record.reviewer else "-",
            str(record.rating),
            record.next_review_date.strftime("%d/%m/%Y") if record.next_review_date else "-",
            record.summary[:80] if record.summary else "-",
        ]
    if section == "disciplinary":
        return [
            record.incident_date.strftime("%d/%m/%Y"),
            record.get_record_type_display(),
            "Yes" if record.resolved else "No",
            record.action_taken[:80] if record.action_taken else "-",
            record.notes[:80] if record.notes else "-",
        ]
    if section == "training":
        return [
            record.training_name,
            record.provider or "-",
            record.completion_date.strftime("%d/%m/%Y") if record.completion_date else "-",
            record.expiry_date.strftime("%d/%m/%Y") if record.expiry_date else "-",
            record.notes[:80] if record.notes else "-",
        ]
    if section == "history":
        return [
            record.get_change_type_display(),
            record.effective_date.strftime("%d/%m/%Y"),
            record.description[:80],
            record.created_by.get_username() if record.created_by else "-",
        ]
    return []


def _staff_management_queryset(request):
    query = request.GET.get("q", "").strip()
    department = request.GET.get("department", "").strip()
    employment_status = request.GET.get("status", "").strip()
    role = request.GET.get("role", "").strip()
    certification_status = request.GET.get("certifications", "").strip()
    roster_employee = request.GET.get("roster", "").strip()
    staff_view = request.GET.get("staff_view", "active").strip() or "active"
    if staff_view not in {"active", "terminated"}:
        staff_view = "active"

    employees = (
        Employee.objects.select_related("supervisor")
        .prefetch_related("qualifications", "leave_requests", "rota_entries", "rotas")
        .order_by("last_name", "first_name")
    )

    show_terminated_only = (
        staff_view == "terminated"
        or employment_status == "terminated"
    )

    if show_terminated_only:
        employees = employees.filter(employment_status="terminated")
    else:
        employees = employees.exclude(employment_status="terminated")

    if query:
        employees = employees.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(employee_id__icontains=query)
            | Q(position__icontains=query)
            | Q(job_title__icontains=query)
            | Q(department__icontains=query)
            | Q(ghana_card_number__icontains=query)
        )
    if department:
        employees = employees.filter(department=department)
    if employment_status:
        if employment_status == "active":
            employees = employees.filter(employment_status="active").exclude(_current_leave_q())
        elif employment_status in EMPLOYMENT_STATUS_TO_LEAVE_TYPE:
            leave_type = EMPLOYMENT_STATUS_TO_LEAVE_TYPE[employment_status]
            employees = employees.filter(
                Q(employment_status=employment_status)
                | Q(
                    leave_requests__leave_type=leave_type,
                    leave_requests__approval_status=LeaveRequest.ApprovalStatus.APPROVED,
                    leave_requests__start_date__lte=timezone.localdate(),
                    leave_requests__end_date__gte=timezone.localdate(),
                )
            )
        else:
            employees = employees.filter(employment_status=employment_status)
    if role:
        employees = employees.filter(position=role)
    if roster_employee:
        if roster_employee.startswith("rota:"):
            rota_id = roster_employee.split(":", 1)[1]
            employees = employees.filter(Q(rota_entries__pk=rota_id) | Q(rotas__pk=rota_id))
        else:
            employees = employees.filter(rota_entries__isnull=False, pk=roster_employee)
    if certification_status == "expiring":
        today = timezone.localdate()
        employees = employees.filter(
            qualifications__expiry_date__isnull=False,
            qualifications__expiry_date__gte=today,
            qualifications__expiry_date__lte=today + timedelta(days=30),
        )
    elif certification_status == "expired":
        employees = employees.filter(
            qualifications__expiry_date__isnull=False,
            qualifications__expiry_date__lt=timezone.localdate(),
        )
    elif certification_status:
        employees = employees.filter(
            qualifications__qualification_name=certification_status
        )

    employees = employees.distinct()

    return {
        "employees": employees,
        "query": query,
        "department": department,
        "employment_status": employment_status,
        "role": role,
        "certification_status": certification_status,
        "selected_roster_employee": roster_employee,
        "staff_view": staff_view,
    }


@group_required("Admin", "Super Administrator", module="staff_management")
def hr_employee_section(request, pk, section):
    employee = get_object_or_404(Employee, pk=pk)
    form_class = _employee_section_form_class(section)
    if form_class is None:
        return redirect("hr-detail", pk=employee.pk)

    staff_filters_token = request.GET.get("staff_filters", "").strip()
    back_to_list_url = reverse("hr-list")
    if staff_filters_token:
        staff_filters_query, _ = _decode_staff_filters_token(staff_filters_token)
        if staff_filters_query:
            back_to_list_url = f"{back_to_list_url}?{staff_filters_query}"

    form = form_class(request.POST or None, request.FILES or None)
    records = _apply_employee_section_filters(
        _employee_section_records(employee, section),
        section,
        request.GET,
    )
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.employee = employee
        if hasattr(record, "approving_manager_id") and not record.approving_manager_id and section == "leave":
            if record.approval_status == LeaveRequest.ApprovalStatus.APPROVED and employee.supervisor_id:
                record.approving_manager = employee.supervisor
        if hasattr(record, "approved_at") and section == "leave":
            if record.approval_status == LeaveRequest.ApprovalStatus.APPROVED and not record.approved_at:
                record.approved_at = timezone.now()
            elif record.approval_status != LeaveRequest.ApprovalStatus.APPROVED:
                record.approved_at = None
        if hasattr(record, "reviewer_id") and not record.reviewer_id and section == "performance":
            record.reviewer = request.user
        if hasattr(record, "created_by_id") and not record.created_by_id and section == "history":
            record.created_by = request.user
        if hasattr(record, "paid_at") and record.payment_status == PayrollRecord.PaymentStatus.PAID and not record.paid_at:
            record.paid_at = timezone.now()
        record.save()
        log_audit_event(
            request=request,
            user=request.user,
            action=AuditLog.ActionType.CREATE,
            module="staff_management",
            object_repr=str(employee),
            object_id=employee.pk,
            details={"section": section, "record": str(record)},
        )
        messages.success(request, f"{_employee_section_title(section)} saved successfully.")
        redirect_url = reverse("hr-employee-section", args=[employee.pk, section])
        if staff_filters_token:
            redirect_url = _append_query_param(
                redirect_url,
                "staff_filters",
                staff_filters_token,
            )
        return redirect(redirect_url)

    return render(
        request,
        "accounts/hr_employee_section.html",
        {
            "employee": employee,
            "section": section,
            "section_title": _employee_section_title(section),
            "headers": _employee_section_headers(section),
            "rows": [_employee_section_row(record, section) for record in records],
            "records": records,
            "record_count": records.count(),
            "form": form,
            "section_filters": _employee_section_filters(section, request.GET),
            "staff_filters_token": staff_filters_token,
            "back_to_list_url": back_to_list_url,
            "section_links": _employee_section_links(
                employee,
                staff_filters_token=staff_filters_token,
                active_section=section,
            ),
        },
    )


@group_required("Admin", "Super Administrator", module="staff_management")
def hr_employee_list(request):
    context = _staff_management_queryset(request)
    context.update(
        {
            "departments": sorted(
                set(
                    Employee.objects.exclude(department="")
                    .values_list("department", flat=True)
                    .distinct()
                )
            ),
            "role_options": _system_role_filter_options(),
            "status_choices": _system_status_filter_options(),
            "certification_filter_options": _system_certification_filter_options(),
            "roster_options": _system_roster_filter_options(),
            "active_count": Employee.objects.exclude(employment_status="terminated").count(),
            "terminated_count": Employee.objects.filter(employment_status="terminated").count(),
            "staff_filters_token": _build_staff_filters_token(request.GET),
        }
    )
    return render(request, "accounts/hr_employee_list.html", context)


@group_required("Admin", "Super Administrator", module="staff_management")
def hr_employee_create(request):
    form = EmployeeForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Employee saved successfully.")
        return redirect("hr-list")
    return render(
        request,
        "accounts/hr_employee_form.html",
        {"form": form, "form_title": "Add New Employee"},
    )


@group_required("Admin", "Super Administrator", module="staff_management")
def hr_employee_update(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    form = EmployeeForm(request.POST or None, request.FILES or None, instance=employee)
    if form.is_valid():
        form.save()
        messages.success(request, "Employee updated successfully.")
        return redirect("hr-list")
    return render(
        request,
        "accounts/hr_employee_form.html",
        {"form": form, "form_title": "Update Employee"},
    )


@group_required("Admin", "Super Administrator", module="staff_management")
def hr_employee_detail(request, pk):
    staff_filters_token = request.GET.get("staff_filters", "").strip()
    back_to_list_url = reverse("hr-list")
    if staff_filters_token:
        staff_filters_query, _ = _decode_staff_filters_token(staff_filters_token)
        if staff_filters_query:
            back_to_list_url = f"{back_to_list_url}?{staff_filters_query}"

    employee = get_object_or_404(
        Employee.objects.select_related("supervisor", "termination_approved_by")
        .prefetch_related("rota_entries", "documents", "qualifications", "leave_requests"),
        pk=pk,
    )
    rotas = employee.rota_entries.order_by("-period_start", "opening_time")
    return render(
        request,
        "accounts/hr_employee_detail.html",
        {
            "employee": employee,
            "rotas": rotas,
            "leave_balance": employee.annual_leave_balance,
            "expiring_certifications_count": employee.expiring_certifications_count,
            "staff_filters_token": staff_filters_token,
            "back_to_list_url": back_to_list_url,
            "section_links": _employee_section_links(
                employee,
                staff_filters_token=staff_filters_token,
            ),
        },
    )


@group_required("Admin", "Super Administrator", module="staff_management")
def hr_employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == "POST":
        employee.delete()
        return redirect("hr-list")
    return render(request, "accounts/hr_employee_confirm_delete.html", {"employee": employee})


@group_required("Admin", "Super Administrator", module="staff_management")
def hr_rota_list(request):
    period, reference_date, start_date, end_date = _parse_rota_range(request)
    query = request.GET.get("q", "").strip()
    employee_id = request.GET.get("employee", "").strip()
    rotas_qs = (
        Rota.objects.select_related("employee")
        .filter(employee__isnull=False, period_start__lte=end_date, period_end__gte=start_date)
        .order_by("-period_start", "employee__last_name", "employee__first_name")
    )
    if query:
        rotas_qs = rotas_qs.filter(
            Q(employee__first_name__icontains=query)
            | Q(employee__last_name__icontains=query)
            | Q(employee__position__icontains=query)
            | Q(period__icontains=query)
        )
    if employee_id:
        rotas_qs = rotas_qs.filter(employee_id=employee_id)
    rotas = list(rotas_qs)

    summary = {
        "total_rotas": len(rotas),
        "total_hours": sum((rota.total_hours for rota in rotas), 0),
        "active_employees": len({rota.employee_id for rota in rotas}),
    }
    return render(
        request,
        "accounts/hr_rota_list.html",
        {
            "rotas": rotas,
            "query": query,
            "period": period,
            "reference_date": reference_date,
            "start_date": start_date,
            "end_date": end_date,
            "summary": summary,
            "day_reports": _rota_day_reports(rotas, start_date, end_date),
            "selected_employee": employee_id,
            "employees": Employee.objects.order_by("last_name", "first_name"),
        },
    )


@group_required("Admin", "Super Administrator", module="staff_management")
def hr_rota_create(request):
    form = RotaForm(request.POST or None)
    if form.is_valid():
        rota = form.save(commit=False)
        if not rota.period:
            rota.period = f"{rota.employee} weekly duty roster"
        rota.save()
        rota.staff_members.set([rota.employee])
        messages.success(request, "Duty roster created successfully.")
        return redirect("hr-rota-list")
    return render(
        request,
        "accounts/hr_rota_form.html",
        {"form": form, "form_title": "Create Weekly Duty Roster"},
    )


@group_required("Admin", "Super Administrator", module="staff_management")
def hr_rota_update(request, pk):
    rota = get_object_or_404(Rota, pk=pk)
    form = RotaForm(request.POST or None, instance=rota)
    if form.is_valid():
        rota = form.save()
        if rota.employee_id:
            rota.staff_members.set([rota.employee])
        messages.success(request, "Duty roster updated successfully.")
        return redirect("hr-rota-list")
    return render(
        request,
        "accounts/hr_rota_form.html",
        {"form": form, "form_title": "Edit Weekly Duty Roster"},
    )


@group_required("Admin", "Super Administrator", module="staff_management")
def hr_rota_detail(request, pk):
    rota = get_object_or_404(Rota.objects.select_related("employee"), pk=pk)
    return render(
        request,
        "accounts/hr_rota_detail.html",
        {
            "rota": rota,
            "daily_roster": _rota_daily_breakdown(rota),
        },
    )


@group_required("Admin")
def admin_reports(request):
    start_date, end_date = _parse_report_range(request)
    today = timezone.localdate()
    total_rooms = Room.objects.count()
    occupied_rooms = Room.objects.filter(status=Room.RoomStatus.OCCUPIED).count()
    active_bookings = Booking.objects.filter(
        status__in=[
            Booking.BookingStatus.PENDING,
            Booking.BookingStatus.CONFIRMED,
            Booking.BookingStatus.CHECKED_IN,
        ]
    ).count()
    payments_total = Payment.objects.aggregate(
        total=Coalesce(
            Sum("amount"),
            Value(0, output_field=DecimalField(max_digits=10, decimal_places=2)),
        )
    )["total"]

    bookings_with_balance = Booking.objects.annotate(
        paid_total=Coalesce(
            Sum("payments__amount"),
            Value(0, output_field=DecimalField(max_digits=10, decimal_places=2)),
        ),
        balance=ExpressionWrapper(
            F("total_amount") - F("paid_total"),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
    )
    outstanding_total = bookings_with_balance.aggregate(
        total=Coalesce(
            Sum("balance", filter=Q(balance__gt=0)),
            Value(0, output_field=DecimalField(max_digits=10, decimal_places=2)),
        )
    )["total"]

    daily_rows = _daily_report_rows(start_date, end_date, total_rooms)
    event_bookings_total = EventBooking.objects.filter(
        event_start__date__range=[start_date, end_date]
    ).count()
    chart_labels = [row["date"] for row in daily_rows]
    revenue_data = [float(row["revenue_collected"]) for row in daily_rows]
    occupancy_data = [row["occupied_rooms"] for row in daily_rows]
    period_revenue_total = sum(revenue_data)

    outstanding_bookings = (
        bookings_with_balance.filter(balance__gt=0)
        .select_related("guest", "room")
        .order_by("-balance")[:20]
    )

    context = {
        "today": today,
        "total_rooms": total_rooms,
        "occupied_rooms": occupied_rooms,
        "active_bookings": active_bookings,
        "payments_total": payments_total,
        "outstanding_total": outstanding_total,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily_rows": daily_rows,
        "period_revenue_total": period_revenue_total,
        "event_bookings_total": event_bookings_total,
        "chart_labels_json": json.dumps(chart_labels),
        "revenue_data_json": json.dumps(revenue_data),
        "occupancy_data_json": json.dumps(occupancy_data),
        "outstanding_bookings": outstanding_bookings,
    }
    return render(request, "accounts/admin_reports.html", context)


@group_required("Admin")
def admin_reports_export_daily_csv(request):
    start_date, end_date = _parse_report_range(request)
    total_rooms = Room.objects.count()
    daily_rows = _daily_report_rows(start_date, end_date, total_rooms)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="daily-report-{start_date}-{end_date}.csv"'
    )
    writer = csv.writer(response)
    writer.writerow(["date", "occupied_rooms", "occupancy_percent", "revenue_collected"])
    for row in daily_rows:
        writer.writerow(
            [
                row["date"],
                row["occupied_rooms"],
                row["occupancy_percent"],
                row["revenue_collected"],
            ]
        )
    return response


@group_required("Admin")
def admin_reports_export_balances_csv(request):
    bookings_with_balance = Booking.objects.annotate(
        paid_total=Coalesce(
            Sum("payments__amount"),
            Value(0, output_field=DecimalField(max_digits=10, decimal_places=2)),
        ),
        balance=ExpressionWrapper(
            F("total_amount") - F("paid_total"),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
    ).filter(balance__gt=0).select_related("guest", "room")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="outstanding-balances.csv"'
    writer = csv.writer(response)
    writer.writerow(
        [
            "booking_id",
            "guest_name",
            "room_number",
            "status",
            "total_amount",
            "amount_paid",
            "balance_due",
        ]
    )
    for booking in bookings_with_balance:
        writer.writerow(
            [
                booking.id,
                f"{booking.guest.first_name} {booking.guest.last_name}",
                booking.room.room_number,
                booking.get_status_display(),
                booking.total_amount,
                booking.paid_total,
                booking.balance,
            ]
        )
    return response


def _parse_report_range(request):
    end_date = timezone.localdate()
    start_date = end_date - timedelta(days=13)

    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")

    try:
        if start_date_str:
            start_date = date.fromisoformat(start_date_str)
        if end_date_str:
            end_date = date.fromisoformat(end_date_str)
    except ValueError:
        pass

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    max_days = 92
    if (end_date - start_date).days > max_days:
        start_date = end_date - timedelta(days=max_days)

    return start_date, end_date


def _parse_rota_range(request):
    period = request.GET.get("period", "week").strip().lower() or "week"
    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")
    reference_date_str = request.GET.get("date")
    reference_date = timezone.localdate()
    custom_start_date = None
    custom_end_date = None

    try:
        if start_date_str:
            custom_start_date = date.fromisoformat(start_date_str)
    except ValueError:
        custom_start_date = None

    try:
        if end_date_str:
            custom_end_date = date.fromisoformat(end_date_str)
    except ValueError:
        custom_end_date = None

    try:
        if reference_date_str:
            reference_date = date.fromisoformat(reference_date_str)
    except ValueError:
        reference_date = timezone.localdate()

    if custom_start_date and custom_end_date:
        if custom_start_date > custom_end_date:
            custom_start_date, custom_end_date = custom_end_date, custom_start_date
        return period, custom_start_date, custom_start_date, custom_end_date
    if custom_start_date:
        return period, custom_start_date, custom_start_date, custom_start_date
    if custom_end_date:
        return period, custom_end_date, custom_end_date, custom_end_date

    if period == "month":
        start_date = reference_date.replace(day=1)
        end_date = reference_date.replace(day=monthrange(reference_date.year, reference_date.month)[1])
    elif period == "year":
        start_date = date(reference_date.year, 1, 1)
        end_date = date(reference_date.year, 12, 31)
    else:
        period = "week"
        start_date = reference_date - timedelta(days=reference_date.weekday())
        end_date = start_date + timedelta(days=6)

    return period, reference_date, start_date, end_date


def _rota_daily_breakdown(rota):
    if not all([rota.period_start, rota.period_end]):
        return []

    day_count = (rota.period_end - rota.period_start).days + 1
    daily_hours = rota.daily_hours if rota.opening_time and rota.closing_time else 0

    rows = []
    for day_index in range(day_count):
        current_day = rota.period_start + timedelta(days=day_index)
        rows.append(
            {
                "date": current_day,
                "day_name": current_day.strftime("%A"),
                "start_time": rota.opening_time,
                "end_time": rota.closing_time,
                "hours": daily_hours,
                "period_label": "Workday",
            }
        )

    return rows


def _rota_day_reports(rotas, start_date, end_date):
    reports = []
    days = [start_date + timedelta(days=idx) for idx in range((end_date - start_date).days + 1)]

    for current_day in days:
        active_rotas = [
            rota
            for rota in rotas
            if rota.period_start and rota.period_end and rota.period_start <= current_day <= rota.period_end
        ]
        reports.append(
            {
                "date": current_day,
                "day_name": current_day.strftime("%A"),
                "rotas": active_rotas,
                "employees": len(active_rotas),
                "hours": sum((rota.daily_hours for rota in active_rotas), 0),
            }
        )

    return reports


def _daily_report_rows(start_date, end_date, total_rooms):
    days = [start_date + timedelta(days=idx) for idx in range((end_date - start_date).days + 1)]

    bookings = Booking.objects.filter(
        status__in=[
            Booking.BookingStatus.CONFIRMED,
            Booking.BookingStatus.CHECKED_IN,
            Booking.BookingStatus.CHECKED_OUT,
        ],
        check_in__lte=end_date,
        check_out__gt=start_date,
    ).values("room_id", "check_in", "check_out")

    payments_by_day = {
        row["day"]: row["total"]
        for row in Payment.objects.filter(paid_at__date__range=[start_date, end_date])
        .annotate(day=TruncDate("paid_at"))
        .values("day")
        .annotate(
            total=Coalesce(
                Sum("amount"),
                Value(0, output_field=DecimalField(max_digits=10, decimal_places=2)),
            )
        )
        .order_by("day")
    }

    daily_rows = []
    for current_day in days:
        occupied_count = 0
        for booking in bookings:
            if booking["check_in"] <= current_day < booking["check_out"]:
                occupied_count += 1

        occupancy_percent = round((occupied_count / total_rooms) * 100, 2) if total_rooms else 0
        daily_rows.append(
            {
                "date": current_day.isoformat(),
                "occupied_rooms": occupied_count,
                "occupancy_percent": occupancy_percent,
                "revenue_collected": payments_by_day.get(current_day, 0),
            }
        )

    return daily_rows


def _recent_activity_feed():
    recent_bookings = Booking.objects.select_related("guest", "room").order_by("-created_at")[:5]
    recent_payments = Payment.objects.select_related("booking__guest", "booking__room").order_by("-paid_at")[:5]
    recent_event_bookings = EventBooking.objects.select_related("guest").order_by("-created_at")[:5]
    recent_event_payments = EventPayment.objects.select_related("event_booking__guest").order_by("-paid_at")[:5]
    recent_rooms = Room.objects.exclude(last_status_changed_at__isnull=True).order_by("-last_status_changed_at")[:5]
    recent_status_changes = StatusHistory.objects.select_related("changed_by", "content_type").order_by("-changed_at")[:10]
    recent_notifications = Notification.objects.order_by("-created_at")[:10]

    feed = []
    for item in recent_bookings:
        feed.append(
            {
                "time": item.created_at,
                "title": f"Booking created for {item.guest}",
                "meta": f"Room {item.room.room_number} · {item.get_status_display()}",
            }
        )
    for item in recent_payments:
        feed.append(
            {
                "time": item.paid_at,
                "title": f"Payment received from {item.booking.guest}",
                "meta": f"Room {item.booking.room.room_number} · GHS {item.amount}",
            }
        )
    for item in recent_event_bookings:
        feed.append(
            {
                "time": item.created_at,
                "title": f"Event booked: {item.event_title}",
                "meta": f"{item.event_space_name} · {item.expected_guests} guests",
            }
        )
    for item in recent_event_payments:
        feed.append(
            {
                "time": item.paid_at,
                "title": f"Event payment received from {item.event_booking.guest}",
                "meta": f"{item.event_booking.event_title} · GHS {item.amount}",
            }
        )
    for item in recent_rooms:
        feed.append(
            {
                "time": item.last_status_changed_at,
                "title": f"Room {item.room_number} status updated",
                "meta": f"{item.get_status_display()} · {item.get_room_type_display()}",
            }
        )
    for history in recent_status_changes:
        feed.append(
            {
                "time": history.changed_at,
                "title": f"{history.object_repr} status changed",
                "meta": f"{history.previous_status or 'Unknown'} → {history.new_status}",
            }
        )
    for notification in recent_notifications:
        feed.append(
            {
                "time": notification.created_at,
                "title": notification.title,
                "meta": notification.message,
            }
        )

    feed.sort(key=lambda row: row["time"], reverse=True)
    return feed[:20]
