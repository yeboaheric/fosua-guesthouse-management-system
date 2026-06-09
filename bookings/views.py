from datetime import date, datetime, time, timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import group_required
from bookings.forms import BookingForm
from bookings.forms import EventBookingForm
from bookings.forms import EventPaymentForm
from bookings.forms import PaymentForm
from bookings.models import Booking, EventBooking, EventPayment, Payment
from rooms.models import Room


def _parse_filter_date(raw_value):
    value = (raw_value or "").strip()
    if not value:
        return "", None
    try:
        return value, date.fromisoformat(value)
    except ValueError:
        return value, None


def _parse_week_value(raw_value):
    value = (raw_value or "").strip()
    if not value:
        return "", None
    try:
        iso_year, iso_week = value.split("-W", 1)
        return value, date.fromisocalendar(int(iso_year), int(iso_week), 1)
    except (TypeError, ValueError):
        return value, None


def _build_operations_url(view_mode, selected_date=None, selected_week=None, range_start="", range_end=""):
    params = {"view": view_mode}
    if selected_date:
        params["date"] = selected_date
    if selected_week:
        params["week"] = selected_week
    if range_start:
        params["range_start"] = range_start
    if range_end:
        params["range_end"] = range_end
    query = urlencode({key: value for key, value in params.items() if value})
    return f"?{query}" if query else ""


def _room_status_at(room, target_moment):
    history_entries = list(room.status_history.order_by("changed_at"))
    relevant_history = [entry for entry in history_entries if entry.changed_at <= target_moment]
    if relevant_history:
        return relevant_history[-1].new_status
    if history_entries and history_entries[0].changed_at > target_moment:
        return history_entries[0].previous_status or None
    if room.created_at and room.created_at <= target_moment:
        return room.status
    return None


def _rooms_in_status_on_date(target_date, status_value):
    target_moment = timezone.make_aware(datetime.combine(target_date, time.max))
    room_type = ContentType.objects.get_for_model(Room)
    rooms = list(
        Room.objects.prefetch_related(
            "status_history",
        ).filter(
            Q(created_at__date__lte=target_date)
            | Q(status_history__content_type=room_type)
        ).distinct().order_by("room_number")
    )
    matching_rooms = []
    for room in rooms:
        if _room_status_at(room, target_moment) == status_value:
            matching_rooms.append(room)
    return matching_rooms


def _operations_snapshot_for_date(target_date):
    check_in_statuses = [
        Booking.BookingStatus.PENDING,
        Booking.BookingStatus.CONFIRMED,
        Booking.BookingStatus.CHECKED_IN,
    ]
    check_out_statuses = [
        Booking.BookingStatus.CHECKED_IN,
        Booking.BookingStatus.CHECKED_OUT,
    ]

    today_check_ins = Booking.objects.select_related("guest", "room").filter(
        check_in=target_date,
        status__in=check_in_statuses,
    )
    today_check_outs = Booking.objects.select_related("guest", "room").filter(
        check_out=target_date,
        status__in=check_out_statuses,
    )
    reservations_made = Booking.objects.select_related("guest", "room").filter(
        created_at__date=target_date
    )
    cancelled_bookings = Booking.objects.select_related("guest", "room").filter(
        status=Booking.BookingStatus.CANCELLED,
        updated_at__date=target_date,
    )
    maintenance_rooms = _rooms_in_status_on_date(target_date, Room.RoomStatus.MAINTENANCE)
    cleaning_rooms = _rooms_in_status_on_date(target_date, Room.RoomStatus.CLEANING)
    today_event_bookings = EventBooking.objects.select_related("guest").filter(
        event_start__date=target_date
    )
    cancelled_event_bookings = EventBooking.objects.select_related("guest").filter(
        status=EventBooking.EventBookingStatus.CANCELLED,
        updated_at__date=target_date,
    )
    return {
        "date": target_date,
        "today_check_ins": today_check_ins,
        "today_check_outs": today_check_outs,
        "reservations_made": reservations_made,
        "cancelled_bookings": cancelled_bookings,
        "maintenance_rooms": maintenance_rooms,
        "cleaning_rooms": cleaning_rooms,
        "today_event_bookings": today_event_bookings,
        "cancelled_event_bookings": cancelled_event_bookings,
        "check_ins_count": today_check_ins.count(),
        "check_outs_count": today_check_outs.count(),
        "reservations_count": reservations_made.count(),
        "cancelled_count": cancelled_bookings.count(),
        "maintenance_count": len(maintenance_rooms),
        "cleaning_count": len(cleaning_rooms),
        "events_count": today_event_bookings.count(),
        "cancelled_events_count": cancelled_event_bookings.count(),
    }


@group_required("Admin", "Receptionist", module="reservations")
def booking_list(request):
    bookings = Booking.objects.select_related("guest", "room", "created_by").annotate(
        paid_total=Coalesce(
            Sum("payments__amount"),
            Value(0, output_field=DecimalField(max_digits=10, decimal_places=2)),
        )
    )
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    check_in_input, check_in_date = _parse_filter_date(request.GET.get("check_in"))
    check_out_input, check_out_date = _parse_filter_date(request.GET.get("check_out"))

    if query:
        bookings = bookings.filter(
            Q(guest__first_name__icontains=query)
            | Q(guest__last_name__icontains=query)
            | Q(guest__ghana_card_number__icontains=query)
            | Q(room__room_number__icontains=query)
            | Q(notes__icontains=query)
        )
    if status:
        bookings = bookings.filter(status=status)
    if check_in_input and check_in_date is None:
        messages.error(request, "Enter a valid check-in date to filter reservations.")
    if check_out_input and check_out_date is None:
        messages.error(request, "Enter a valid check-out date to filter reservations.")
    if check_in_date and check_out_date and check_out_date < check_in_date:
        messages.error(request, "Check-out filter date must be on or after the check-in filter date.")
    else:
        if check_in_date:
            bookings = bookings.filter(check_in__gte=check_in_date)
        if check_out_date:
            bookings = bookings.filter(check_out__lte=check_out_date)
    return render(
        request,
        "bookings/booking_list.html",
        {
            "bookings": bookings.order_by("-created_at"),
            "status_choices": Booking.BookingStatus.choices,
            "query": query,
            "selected_status": status or "",
            "check_in": check_in_input,
            "check_out": check_out_input,
        },
    )


@group_required("Admin", "Receptionist", module="reservations")
def booking_create(request):
    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    bookings_to_create = []
                    for room in form.cleaned_data["rooms"]:
                        booking = Booking(
                            guest=form.cleaned_data["guest"],
                            room=room,
                            check_in=form.cleaned_data["check_in"],
                            check_in_time=form.cleaned_data.get("check_in_time"),
                            check_out=form.cleaned_data["check_out"],
                            check_out_time=form.cleaned_data.get("check_out_time"),
                            adults=form.cleaned_data["adults"],
                            children=form.cleaned_data["children"],
                            status=form.cleaned_data["status"],
                            notes=form.cleaned_data["notes"],
                            created_by=request.user,
                        )
                        booking.full_clean()
                        bookings_to_create.append(booking)

                    for booking in bookings_to_create:
                        booking.save()
            except ValidationError as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(
                    request,
                    f"{len(bookings_to_create)} room booking(s) created successfully.",
                )
                return redirect("booking-list")
    else:
        form = BookingForm(
            initial={
                "status": Booking.BookingStatus.PENDING,
                "adults": 1,
                "children": 0,
            }
        )
    return render(
        request,
        "bookings/booking_form.html",
        {"form": form, "title": "New Booking"},
    )


@group_required("Admin", "Receptionist", module="reservations")
def booking_update(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if request.method == "POST":
        form = BookingForm(request.POST, instance=booking)
        if form.is_valid():
            try:
                form.save()
            except ValidationError as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, "Booking updated successfully.")
                return redirect("booking-list")
    else:
        form = BookingForm(instance=booking)

    return render(
        request,
        "bookings/booking_form.html",
        {"form": form, "title": "Edit Booking"},
    )


@group_required("Admin", "Receptionist", module="reservations")
def booking_detail(request, pk):
    booking = get_object_or_404(Booking.objects.select_related("guest", "room"), pk=pk)
    related_bookings = _grouped_guest_bookings(booking)
    payments = Payment.objects.filter(booking__in=related_bookings).select_related(
        "received_by", "booking__room"
    )
    context = {
        "booking": booking,
        "related_bookings": related_bookings,
        "payments": payments,
        "status_history": booking.status_history.select_related("changed_by").order_by("-changed_at"),
        "group_total": sum(item.total_amount for item in related_bookings),
        "group_paid": sum(item.amount_paid for item in related_bookings),
        "group_balance": sum(item.balance_due for item in related_bookings),
    }
    return render(request, "bookings/booking_detail.html", context)


@require_POST
@group_required("Admin", "Receptionist", module="reservations")
def booking_confirm(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if booking.status == Booking.BookingStatus.PENDING:
        booking.status = Booking.BookingStatus.CONFIRMED
        booking.save(update_fields=["status", "updated_at"])
        messages.success(request, "Booking confirmed.")
    return redirect("booking-list")


@require_POST
@group_required("Admin", "Receptionist", module="reservations")
def booking_check_in(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if booking.status in [Booking.BookingStatus.CONFIRMED, Booking.BookingStatus.PENDING]:
        booking.status = Booking.BookingStatus.CHECKED_IN
        booking.save(update_fields=["status", "updated_at"])
        room = booking.room
        room.status = Room.RoomStatus.OCCUPIED
        room.save()
        messages.success(request, "Guest checked in.")
    return redirect("booking-list")


@require_POST
@group_required("Admin", "Receptionist", module="reservations")
def booking_check_out(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if booking.status == Booking.BookingStatus.CHECKED_IN:
        booking.status = Booking.BookingStatus.CHECKED_OUT
        booking.save(update_fields=["status", "updated_at"])
        room = booking.room
        room.status = Room.RoomStatus.AVAILABLE
        room.save()
        messages.success(request, "Guest checked out.")
    return redirect("booking-list")


@require_POST
@group_required("Admin", "Receptionist", module="reservations")
def booking_cancel(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if booking.status in [Booking.BookingStatus.PENDING, Booking.BookingStatus.CONFIRMED]:
        booking.status = Booking.BookingStatus.CANCELLED
        booking.save(update_fields=["status", "updated_at"])
        messages.success(request, "Booking cancelled.")
    return redirect("booking-list")


@group_required("Admin", "Receptionist", module="payments")
def booking_payments(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related("guest", "room").prefetch_related("payments"),
        pk=pk,
    )

    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.booking = booking
            payment.received_by = request.user
            payment.save()
            messages.success(request, "Payment recorded successfully.")
            return redirect("booking-payments", pk=booking.pk)
    else:
        form = PaymentForm()

    return render(
        request,
        "bookings/booking_payments.html",
        {
            "booking": booking,
            "form": form,
            "payments": booking.payments.select_related("received_by"),
            "related_bookings": _grouped_guest_bookings(booking),
        },
    )


@group_required("Admin", "Receptionist", module="services")
def event_booking_list(request):
    event_bookings = EventBooking.objects.select_related("guest", "created_by").annotate(
        paid_total=Coalesce(
            Sum("payments__amount"),
            Value(0, output_field=DecimalField(max_digits=10, decimal_places=2)),
        )
    )
    status = request.GET.get("status")
    if status:
        event_bookings = event_bookings.filter(status=status)
    return render(
        request,
        "bookings/event_booking_list.html",
        {
            "event_bookings": event_bookings,
            "status_choices": EventBooking.EventBookingStatus.choices,
        },
    )


@group_required("Admin", "Receptionist", module="services")
def event_booking_create(request):
    if request.method == "POST":
        form = EventBookingForm(request.POST)
        if form.is_valid():
            event_booking = form.save(commit=False)
            event_booking.created_by = request.user
            try:
                event_booking.save()
            except ValidationError as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, "Event space booking created successfully.")
                return redirect("event-booking-list")
    else:
        form = EventBookingForm(
            initial={
                "status": EventBooking.EventBookingStatus.PENDING,
                "event_space_name": "Main Event Space",
                "expected_guests": 20,
            }
        )
    return render(
        request,
        "bookings/event_booking_form.html",
        {"form": form, "title": "New Event Space Booking"},
    )


@group_required("Admin", "Receptionist", module="services")
def event_booking_update(request, pk):
    event_booking = get_object_or_404(EventBooking, pk=pk)
    if request.method == "POST":
        form = EventBookingForm(request.POST, instance=event_booking)
        if form.is_valid():
            try:
                form.save()
            except ValidationError as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, "Event space booking updated successfully.")
                return redirect("event-booking-list")
    else:
        form = EventBookingForm(instance=event_booking)
    return render(
        request,
        "bookings/event_booking_form.html",
        {"form": form, "title": "Edit Event Space Booking"},
    )


@require_POST
@group_required("Admin", "Receptionist", module="services")
def event_booking_confirm(request, pk):
    event_booking = get_object_or_404(EventBooking, pk=pk)
    if event_booking.status == EventBooking.EventBookingStatus.PENDING:
        event_booking.status = EventBooking.EventBookingStatus.CONFIRMED
        event_booking.save(update_fields=["status", "updated_at"])
        messages.success(request, "Event booking confirmed.")
    return redirect("event-booking-list")


@require_POST
@group_required("Admin", "Receptionist", module="services")
def event_booking_start(request, pk):
    event_booking = get_object_or_404(EventBooking, pk=pk)
    if event_booking.status in [
        EventBooking.EventBookingStatus.PENDING,
        EventBooking.EventBookingStatus.CONFIRMED,
    ]:
        event_booking.status = EventBooking.EventBookingStatus.IN_PROGRESS
        event_booking.save(update_fields=["status", "updated_at"])
        messages.success(request, "Event marked in progress.")
    return redirect("event-booking-list")


@require_POST
@group_required("Admin", "Receptionist", module="services")
def event_booking_complete(request, pk):
    event_booking = get_object_or_404(EventBooking, pk=pk)
    if event_booking.status == EventBooking.EventBookingStatus.IN_PROGRESS:
        event_booking.status = EventBooking.EventBookingStatus.COMPLETED
        event_booking.save(update_fields=["status", "updated_at"])
        messages.success(request, "Event marked completed.")
    return redirect("event-booking-list")


@require_POST
@group_required("Admin", "Receptionist", module="services")
def event_booking_cancel(request, pk):
    event_booking = get_object_or_404(EventBooking, pk=pk)
    if event_booking.status in [
        EventBooking.EventBookingStatus.PENDING,
        EventBooking.EventBookingStatus.CONFIRMED,
    ]:
        event_booking.status = EventBooking.EventBookingStatus.CANCELLED
        event_booking.save(update_fields=["status", "updated_at"])
        messages.success(request, "Event booking cancelled.")
    return redirect("event-booking-list")


@group_required("Admin", "Receptionist", module="payments")
def event_booking_payments(request, pk):
    event_booking = get_object_or_404(
        EventBooking.objects.select_related("guest").prefetch_related("payments"),
        pk=pk,
    )

    if request.method == "POST":
        form = EventPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.event_booking = event_booking
            payment.received_by = request.user
            payment.save()
            messages.success(request, "Event payment recorded successfully.")
            return redirect("event-booking-payments", pk=event_booking.pk)
    else:
        form = EventPaymentForm()

    return render(
        request,
        "bookings/event_booking_payments.html",
        {
            "event_booking": event_booking,
            "form": form,
            "payments": event_booking.payments.select_related("received_by"),
        },
    )


@group_required("Admin", "Receptionist", module="dashboard")
def operations_overview(request):
    today = timezone.localdate()
    view_mode = request.GET.get("view", "daily").strip().lower() or "daily"
    if view_mode not in {"daily", "weekly"}:
        view_mode = "daily"

    date_input, selected_date = _parse_filter_date(request.GET.get("date"))
    week_input, selected_week_start = _parse_week_value(request.GET.get("week"))
    range_start_input, range_start = _parse_filter_date(request.GET.get("range_start"))
    range_end_input, range_end = _parse_filter_date(request.GET.get("range_end"))

    if date_input and selected_date is None:
        messages.error(request, "Enter a valid date for Operations Overview.")
    if week_input and selected_week_start is None:
        messages.error(request, "Enter a valid week for Operations Overview.")
    if range_start_input and range_start is None:
        messages.error(request, "Enter a valid range start date.")
    if range_end_input and range_end is None:
        messages.error(request, "Enter a valid range end date.")

    using_custom_range = False
    if view_mode == "weekly":
        if range_start and range_end:
            if range_end < range_start:
                range_start, range_end = range_end, range_start
            start_date = range_start
            end_date = range_end
            using_custom_range = True
        else:
            base_date = selected_week_start or selected_date or today
            start_date = base_date - timedelta(days=base_date.weekday())
            end_date = start_date + timedelta(days=6)
        selected_day = selected_date or start_date
        daily_snapshot = None
        week_days = []
        current_day = start_date
        while current_day <= end_date:
            snapshot = _operations_snapshot_for_date(current_day)
            week_days.append(
                {
                    "date": current_day,
                    "day_name": current_day.strftime("%A"),
                    "snapshot": snapshot,
                }
            )
            current_day += timedelta(days=1)
        totals = {
            "check_ins": sum(day["snapshot"]["check_ins_count"] for day in week_days),
            "check_outs": sum(day["snapshot"]["check_outs_count"] for day in week_days),
            "reservations": sum(day["snapshot"]["reservations_count"] for day in week_days),
            "cancelled": sum(day["snapshot"]["cancelled_count"] for day in week_days),
            "maintenance": sum(day["snapshot"]["maintenance_count"] for day in week_days),
            "cleaning": sum(day["snapshot"]["cleaning_count"] for day in week_days),
            "events": sum(day["snapshot"]["events_count"] for day in week_days),
            "cancelled_events": sum(day["snapshot"]["cancelled_events_count"] for day in week_days),
        }
        range_label = (
            f"{start_date:%d %b %Y} - {end_date:%d %b %Y}"
            if using_custom_range or start_date != end_date
            else start_date.strftime("%d %b %Y")
        )
        if using_custom_range:
            previous_start = start_date - timedelta(days=(end_date - start_date).days + 1)
            previous_end = end_date - timedelta(days=(end_date - start_date).days + 1)
            next_start = start_date + timedelta(days=(end_date - start_date).days + 1)
            next_end = end_date + timedelta(days=(end_date - start_date).days + 1)
            previous_url = _build_operations_url(
                "weekly",
                selected_date="",
                selected_week="",
                range_start=previous_start.isoformat(),
                range_end=previous_end.isoformat(),
            )
            next_url = _build_operations_url(
                "weekly",
                selected_date="",
                selected_week="",
                range_start=next_start.isoformat(),
                range_end=next_end.isoformat(),
            )
        else:
            previous_url = _build_operations_url(
                "weekly",
                selected_date=(start_date - timedelta(days=7)).isoformat(),
                selected_week=(start_date - timedelta(days=7)).strftime("%G-W%V"),
            )
            next_url = _build_operations_url(
                "weekly",
                selected_date=(start_date + timedelta(days=7)).isoformat(),
                selected_week=(start_date + timedelta(days=7)).strftime("%G-W%V"),
            )
    else:
        selected_day = selected_date or today
        daily_snapshot = _operations_snapshot_for_date(selected_day)
        week_days = []
        totals = None
        start_date = selected_day
        end_date = selected_day
        range_label = selected_day.strftime("%d %b %Y")
        previous_url = _build_operations_url(
            "daily",
            selected_date=(selected_day - timedelta(days=1)).isoformat(),
        )
        next_url = _build_operations_url(
            "daily",
            selected_date=(selected_day + timedelta(days=1)).isoformat(),
        )

    context = {
        "today": today,
        "view_mode": view_mode,
        "selected_date": selected_day,
        "selected_date_input": selected_day.isoformat(),
        "selected_week_input": start_date.strftime("%G-W%V"),
        "range_start_input": range_start_input or start_date.isoformat(),
        "range_end_input": range_end_input or end_date.isoformat(),
        "range_label": range_label,
        "previous_url": previous_url,
        "next_url": next_url,
        "today_url": _build_operations_url("daily", selected_date=today.isoformat()),
        "week_view_url": _build_operations_url(
            "weekly",
            selected_date=selected_day.isoformat(),
            selected_week=(selected_week_start or start_date).strftime("%G-W%V"),
            range_start=range_start_input if using_custom_range else "",
            range_end=range_end_input if using_custom_range else "",
        ),
        "day_view_url": _build_operations_url("daily", selected_date=selected_day.isoformat()),
        "week_days": week_days,
        "weekly_totals": totals,
        "using_custom_range": using_custom_range,
    }
    if daily_snapshot is not None:
        context.update(daily_snapshot)
    return render(request, "bookings/operations_overview.html", context)


def _grouped_guest_bookings(booking):
    return list(
        Booking.objects.select_related("guest", "room")
        .filter(
            guest=booking.guest,
            check_in=booking.check_in,
            check_out=booking.check_out,
        )
        .order_by("room__room_number", "created_at")
    )
