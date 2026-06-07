from calendar import monthrange
from datetime import datetime, time, timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib import messages
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import group_required
from bookings.models import Booking
from rooms.forms import HousekeepingItemLogForm, RoomForm
from rooms.models import HousekeepingItemLog, Room


ZERO_UNITS = Value(0, output_field=DecimalField(max_digits=12, decimal_places=3))


def _recalculate_all_stock_levels():
    HousekeepingItemLog.objects.update(
        quantity_in_stock=ExpressionWrapper(
            F("initial_quantity") - F("quantity_used"),
            output_field=DecimalField(max_digits=12, decimal_places=3),
        )
    )


def _latest_item_entries():
    latest_entries = {}
    entries = HousekeepingItemLog.objects.select_related("room", "created_by").order_by(
        "item_name",
        "unit",
        "-used_at",
        "-created_at",
    )
    for entry in entries:
        key = (entry.item_name.strip().lower(), entry.unit.strip().lower())
        latest_entries.setdefault(key, entry)
    return list(latest_entries.values())


def _housekeeping_inventory_summary():
    latest_entries = _latest_item_entries()
    total_initial_stock = sum((entry.initial_quantity for entry in latest_entries), Decimal("0.000"))
    total_items_used = sum((entry.quantity_used for entry in latest_entries), Decimal("0.000"))
    total_items_in_stock = sum((entry.quantity_in_stock for entry in latest_entries), Decimal("0.000"))
    low_stock_entries = [entry for entry in latest_entries if entry.is_low_stock]
    return {
        "latest_entries": latest_entries,
        "total_initial_stock": total_initial_stock,
        "total_items_used": total_items_used,
        "total_items_in_stock": total_items_in_stock,
        "low_stock_entries": low_stock_entries,
        "low_stock_count": len(low_stock_entries),
    }


@group_required("Admin", "Receptionist", module="rooms")
def room_list(request):
    rooms = Room.objects.all()
    context = {
        "rooms": rooms,
        "standard_count": rooms.filter(room_type=Room.RoomType.STANDARD).count(),
        "deluxe_count": rooms.filter(room_type=Room.RoomType.DELUXE).count(),
        "maintenance_count": rooms.filter(status=Room.RoomStatus.MAINTENANCE).count(),
        "cleaning_count": rooms.filter(status=Room.RoomStatus.CLEANING).count(),
    }
    return render(request, "rooms/room_list.html", context)


@group_required("Admin")
def room_create(request):
    if request.method == "POST":
        form = RoomForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Room created successfully.")
            return redirect("room-list")
    else:
        form = RoomForm()
    return render(request, "rooms/room_form.html", {"form": form, "title": "Add Room"})


@group_required("Admin")
def room_update(request, pk):
    room = get_object_or_404(Room, pk=pk)
    if request.method == "POST":
        form = RoomForm(request.POST, instance=room)
        if form.is_valid():
            form.save()
            messages.success(request, "Room updated successfully.")
            return redirect("room-list")
    else:
        form = RoomForm(instance=room)
    return render(request, "rooms/room_form.html", {"form": form, "title": "Edit Room"})


@group_required("Admin", "Receptionist", module="rooms")
def room_availability(request):
    check_in = request.GET.get("check_in")
    check_out = request.GET.get("check_out")
    available_rooms = None

    if check_in and check_out:
        try:
            check_in_date = datetime.fromisoformat(check_in).date()
            check_out_date = datetime.fromisoformat(check_out).date()
            if check_out_date <= check_in_date:
                messages.error(request, "Check-out must be after check-in.")
                return render(
                    request,
                    "rooms/availability.html",
                    {
                        "available_rooms": None,
                        "check_in": check_in,
                        "check_out": check_out,
                    },
                )
        except ValueError:
            messages.error(request, "Please enter valid dates.")
            return render(
                request,
                "rooms/availability.html",
                {
                    "available_rooms": None,
                    "check_in": check_in,
                    "check_out": check_out,
                },
            )

        active_statuses = [
            Booking.BookingStatus.PENDING,
            Booking.BookingStatus.CONFIRMED,
            Booking.BookingStatus.CHECKED_IN,
        ]
        unavailable_room_ids = Booking.objects.filter(
            status__in=active_statuses,
            check_in__lt=check_out_date,
            check_out__gt=check_in_date,
        ).values_list("room_id", flat=True)

        available_rooms = Room.objects.filter(status=Room.RoomStatus.AVAILABLE).exclude(
            id__in=unavailable_room_ids
        )

    return render(
        request,
        "rooms/availability.html",
        {
            "available_rooms": available_rooms,
            "check_in": check_in,
            "check_out": check_out,
        },
    )


def _report_window(report_range):
    today = timezone.localdate()
    if report_range == "weekly":
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
        label = f"{start_date:%d %b %Y} - {end_date:%d %b %Y}"
        filename_suffix = f"{start_date.isoformat()}-to-{end_date.isoformat()}"
    elif report_range == "monthly":
        start_date = today.replace(day=1)
        end_date = today.replace(day=monthrange(today.year, today.month)[1])
        label = today.strftime("%B %Y")
        filename_suffix = today.strftime("%Y-%m")
    elif report_range == "yearly":
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
        label = today.strftime("%Y")
        filename_suffix = today.strftime("%Y")
    else:
        report_range = "daily"
        start_date = today
        end_date = today
        label = today.strftime("%d %b %Y")
        filename_suffix = today.isoformat()
    return {
        "key": report_range,
        "start_date": start_date,
        "end_date": end_date,
        "label": label,
        "filename_suffix": filename_suffix,
    }


def _report_queryset(report_range):
    window = _report_window(report_range)
    queryset = HousekeepingItemLog.objects.select_related("room", "created_by").filter(
        used_at__date__range=(window["start_date"], window["end_date"])
    )
    return window, queryset


def _report_summary(report_range):
    window, queryset = _report_queryset(report_range)
    summary_rows = list(
        queryset.values("item_name", "unit")
        .annotate(
            total_initial_quantity=Coalesce(Sum("initial_quantity"), ZERO_UNITS),
            total_quantity=Coalesce(Sum("quantity_used"), ZERO_UNITS),
            total_quantity_in_stock=Coalesce(Sum("quantity_in_stock"), ZERO_UNITS),
            entry_count=Count("id"),
        )
        .order_by("item_name", "unit")
    )
    return {
        "window": window,
        "entries": queryset.order_by("-used_at", "-created_at"),
        "summary_rows": summary_rows,
        "total_entries": queryset.count(),
        "total_initial_quantity": queryset.aggregate(
            total=Coalesce(Sum("initial_quantity"), ZERO_UNITS)
        )["total"],
        "total_items_consumed": queryset.aggregate(
            total=Coalesce(Sum("quantity_used"), ZERO_UNITS)
        )["total"],
        "total_items_in_stock": queryset.aggregate(
            total=Coalesce(Sum("quantity_in_stock"), ZERO_UNITS)
        )["total"],
    }


def _dashboard_context(form, report_range, editing_entry=None):
    _recalculate_all_stock_levels()
    report = _report_summary(report_range)
    inventory_summary = _housekeeping_inventory_summary()
    return {
        "form": form,
        "editing_entry": editing_entry,
        "entries": HousekeepingItemLog.objects.select_related("room", "created_by").order_by("-used_at", "-created_at"),
        "summary_total_initial_stock": inventory_summary["total_initial_stock"],
        "summary_total_items_used": inventory_summary["total_items_used"],
        "summary_total_items_in_stock": inventory_summary["total_items_in_stock"],
        "low_stock_entries": inventory_summary["low_stock_entries"],
        "low_stock_count": inventory_summary["low_stock_count"],
        "report_range": report["window"]["key"],
        "report_label": report["window"]["label"],
        "report_start_date": report["window"]["start_date"],
        "report_end_date": report["window"]["end_date"],
        "report_summary_rows": report["summary_rows"],
        "report_total_entries": report["total_entries"],
        "report_total_initial_quantity": report["total_initial_quantity"],
        "report_total_items_consumed": report["total_items_consumed"],
        "report_total_items_in_stock": report["total_items_in_stock"],
        "report_filename_suffix": report["window"]["filename_suffix"],
    }


@group_required("Admin", "Receptionist", "Housekeeping", module="housekeeping")
def housekeeping_dashboard(request):
    report_range = request.GET.get("report", "daily")
    form = HousekeepingItemLogForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        entry = form.save(commit=False)
        entry.created_by = request.user
        entry.save()
        _recalculate_all_stock_levels()
        messages.success(request, "Usage entry logged.")
        return redirect(f"{request.path}?report={report_range}")
    return render(
        request,
        "rooms/housekeeping_dashboard.html",
        _dashboard_context(form, report_range),
    )


@group_required("Admin", "Receptionist", "Housekeeping", module="housekeeping")
def housekeeping_log_edit(request, pk):
    entry = get_object_or_404(HousekeepingItemLog, pk=pk)
    report_range = request.GET.get("report", "daily")
    form = HousekeepingItemLogForm(request.POST or None, instance=entry)
    if request.method == "POST" and form.is_valid():
        form.save()
        _recalculate_all_stock_levels()
        messages.success(request, "Usage entry updated.")
        return redirect(f"{reverse('housekeeping-dashboard')}?report={report_range}")
    return render(
        request,
        "rooms/housekeeping_dashboard.html",
        _dashboard_context(form, report_range, editing_entry=entry),
    )


@require_POST
@group_required("Admin", "Receptionist", "Housekeeping", module="housekeeping")
def housekeeping_log_delete(request, pk):
    entry = get_object_or_404(HousekeepingItemLog, pk=pk)
    report_range = request.GET.get("report", "daily")
    entry.delete()
    _recalculate_all_stock_levels()
    messages.success(request, "Usage entry deleted.")
    return redirect(f"{reverse('housekeeping-dashboard')}?report={report_range}")


@group_required("Admin", "Receptionist", "Housekeeping", module="housekeeping")
def housekeeping_report_export(request, report_range):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
    except ImportError:
        messages.error(request, "openpyxl is required for Excel export.")
        return redirect("housekeeping-dashboard")

    report = _report_summary(report_range)
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = f"{report['window']['key'].title()} Report"

    worksheet.append(["Housekeeping Items Usage Report"])
    worksheet.append([f"Range: {report['window']['label']}"])
    worksheet.append([])
    worksheet.append(
        [
            "Item Name",
            "Total Initial Qty",
            "Total Quantity Used",
            "Total Quantity in Stock",
            "Unit",
            "Number of Entries",
        ]
    )

    for cell in worksheet[4]:
        cell.font = Font(bold=True)

    for row in report["summary_rows"]:
        worksheet.append(
            [
                row["item_name"],
                float(row["total_initial_quantity"]),
                float(row["total_quantity"]),
                float(row["total_quantity_in_stock"]),
                row["unit"],
                row["entry_count"],
            ]
        )

    worksheet.append([])
    worksheet.append(
        [
            "TOTALS",
            float(report["total_initial_quantity"]),
            float(report["total_items_consumed"]),
            float(report["total_items_in_stock"]),
            "",
            report["total_entries"],
        ]
    )
    for cell in worksheet[worksheet.max_row]:
        cell.font = Font(bold=True)

    worksheet.column_dimensions["A"].width = 28
    worksheet.column_dimensions["B"].width = 20
    worksheet.column_dimensions["C"].width = 20
    worksheet.column_dimensions["D"].width = 20
    worksheet.column_dimensions["E"].width = 16
    worksheet.column_dimensions["F"].width = 18

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    filename = (
        f"housekeeping-report-{report['window']['key']}-"
        f"{report['window']['filename_suffix']}.xlsx"
    )
    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
