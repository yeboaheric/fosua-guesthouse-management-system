import csv
import json
from datetime import date, timedelta

from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.db.models.functions import TruncDate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.decorators import group_required
from bookings.models import Booking, Payment
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


@login_required
def dashboard(request):
    if request.user.is_superuser or _is_group_member(request.user, "Admin"):
        return redirect("admin-dashboard")

    if _is_group_member(request.user, "Receptionist"):
        return redirect("reception-dashboard")

    return render(request, "accounts/dashboard.html")


@group_required("Admin")
def admin_dashboard(request):
    return render(request, "accounts/admin_dashboard.html")


@group_required("Receptionist", "Admin")
def reception_dashboard(request):
    return render(request, "accounts/reception_dashboard.html")


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
