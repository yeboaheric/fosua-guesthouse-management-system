import csv
import json
from calendar import monthrange
from itertools import chain
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.db.models.functions import TruncDate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts.decorators import group_required
from accounts.forms import EmployeeForm, RotaForm, StaffRoleForm, StaffUserForm
from accounts.models import Employee, Rota, UserAccessProfile
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
    if user.is_superuser or _is_group_member(user, "Admin"):
        return True
    access_profile, _ = UserAccessProfile.objects.get_or_create(
        user=user,
        defaults={
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
            "reports_access": False,
            "settings_access": False,
            "staff_management_access": False,
            "handovers_access": True,
            "users_roles_access": False,
        },
    )
    return access_profile.has_module_access(module_name)


def _dashboard_snapshot():
    today = timezone.localdate()
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

    return {
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


@login_required
def dashboard(request):
    if request.user.is_superuser or _is_group_member(request.user, "Admin"):
        return redirect("admin-dashboard")

    if _is_group_member(request.user, "Receptionist"):
        return redirect("reception-dashboard")

    return render(request, "accounts/dashboard.html")


@group_required("Admin")
def admin_dashboard(request):
    context = _dashboard_snapshot()
    context["role_label"] = "Admin"
    return render(request, "accounts/admin_dashboard.html", context)


@group_required("Receptionist", "Admin", module="dashboard")
def reception_dashboard(request):
    context = _dashboard_snapshot()
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
                | Q(sku__icontains=query)
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
    rooms = Room.objects.all().order_by("room_number")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    room_type = request.GET.get("room_type", "")

    if query:
        rooms = rooms.filter(
            Q(room_number__icontains=query)
            | Q(notes__icontains=query)
        )
    if status:
        rooms = rooms.filter(status=status)
    if room_type:
        rooms = rooms.filter(room_type=room_type)

    return render(
        request,
        "accounts/housekeeping_center.html",
        {
            "available_rooms": rooms.filter(status=Room.RoomStatus.AVAILABLE),
            "occupied_rooms": rooms.filter(status=Room.RoomStatus.OCCUPIED),
            "cleaning_rooms": rooms.filter(status=Room.RoomStatus.CLEANING),
            "maintenance_rooms": rooms.filter(status=Room.RoomStatus.MAINTENANCE),
            "recent_rooms": rooms.order_by("-last_status_changed_at")[:8],
            "query": query,
            "selected_status": status,
            "selected_room_type": room_type,
            "room_status_choices": Room.RoomStatus.choices,
            "room_type_choices": Room.RoomType.choices,
        },
    )


@group_required("Admin", "Receptionist", module="notifications")
def notifications_center(request):
    return render(
        request,
        "accounts/notifications_center.html",
        {"activities": _recent_activity_feed()},
    )


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


@group_required("Admin")
def users_roles_center(request):
    for role_name in ("Admin", "Receptionist"):
        Group.objects.get_or_create(name=role_name)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create_user":
            create_form = StaffUserForm(request.POST)
            if create_form.is_valid():
                user = create_form.save()
                messages.success(request, f"User '{user.username}' created successfully.")
                return redirect("users-roles-center")
        elif action == "update_user":
            user = get_object_or_404(User, pk=request.POST.get("user_id"))
            role_form = StaffRoleForm(request.POST, user=user)
            if role_form.is_valid():
                role_form.save()
                messages.success(request, f"Roles updated for '{user.username}'.")
                return redirect("users-roles-center")
        else:
            create_form = StaffUserForm()
    else:
        create_form = StaffUserForm()

    users = User.objects.prefetch_related("groups").order_by("username")
    role_forms = {user.pk: StaffRoleForm(user=user, initial={"user_id": user.pk}) for user in users}
    return render(
        request,
        "accounts/users_roles_center.html",
        {
            "create_form": create_form,
            "users": users,
            "role_forms": role_forms,
            "available_roles": Group.objects.filter(name__in=["Admin", "Receptionist"]).order_by("name"),
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


@group_required("Admin")
def hr_employee_list(request):
    query = request.GET.get("q", "").strip()
    employees = Employee.objects.all().order_by("last_name", "first_name")
    if query:
        employees = employees.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(position__icontains=query)
            | Q(ghana_card_number__icontains=query)
        )
    return render(
        request,
        "accounts/hr_employee_list.html",
        {"employees": employees, "query": query},
    )


@group_required("Admin")
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


@group_required("Admin")
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


@group_required("Admin")
def hr_employee_detail(request, pk):
    employee = get_object_or_404(Employee.objects.prefetch_related("rota_entries"), pk=pk)
    rotas = employee.rota_entries.order_by("-period_start", "opening_time")
    return render(
        request,
        "accounts/hr_employee_detail.html",
        {"employee": employee, "rotas": rotas},
    )


@group_required("Admin")
def hr_employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == "POST":
        employee.delete()
        return redirect("hr-list")
    return render(request, "accounts/hr_employee_confirm_delete.html", {"employee": employee})


@group_required("Admin")
def hr_rota_list(request):
    period, reference_date, start_date, end_date = _parse_rota_range(request)
    query = request.GET.get("q", "").strip()
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
        },
    )


@group_required("Admin")
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


@group_required("Admin")
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


@group_required("Admin")
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
    reference_date_str = request.GET.get("date")
    reference_date = timezone.localdate()

    try:
        if reference_date_str:
            reference_date = date.fromisoformat(reference_date_str)
    except ValueError:
        reference_date = timezone.localdate()

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

    feed.sort(key=lambda row: row["time"], reverse=True)
    return feed[:12]
