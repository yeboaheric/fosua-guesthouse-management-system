from django.contrib import messages
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


@group_required("Admin", "Receptionist", module="reservations")
def booking_list(request):
    bookings = Booking.objects.select_related("guest", "room", "created_by").annotate(
        paid_total=Coalesce(
            Sum("payments__amount"),
            Value(0, output_field=DecimalField(max_digits=10, decimal_places=2)),
        )
    )
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status")
    check_in = request.GET.get("check_in")
    check_out = request.GET.get("check_out")

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
    if check_in:
        bookings = bookings.filter(check_in=check_in)
    if check_out:
        bookings = bookings.filter(check_out=check_out)
    return render(
        request,
        "bookings/booking_list.html",
        {
            "bookings": bookings,
            "status_choices": Booking.BookingStatus.choices,
            "query": query,
            "selected_status": status or "",
            "check_in": check_in or "",
            "check_out": check_out or "",
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
                            check_out=form.cleaned_data["check_out"],
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


@group_required("Admin", "Receptionist", module="housekeeping")
def operations_overview(request):
    today = timezone.localdate()

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
        check_in=today,
        status__in=check_in_statuses,
    )
    today_check_outs = Booking.objects.select_related("guest", "room").filter(
        check_out=today,
        status__in=check_out_statuses,
    )
    reservations_made = Booking.objects.select_related("guest", "room").filter(
        created_at__date=today
    )
    cancelled_bookings = Booking.objects.select_related("guest", "room").filter(
        status=Booking.BookingStatus.CANCELLED,
        updated_at__date=today,
    )
    maintenance_rooms = Room.objects.filter(status=Room.RoomStatus.MAINTENANCE)
    cleaning_rooms = Room.objects.filter(status=Room.RoomStatus.CLEANING)
    today_event_bookings = EventBooking.objects.select_related("guest").filter(
        event_start__date=today
    )
    cancelled_event_bookings = EventBooking.objects.select_related("guest").filter(
        status=EventBooking.EventBookingStatus.CANCELLED,
        updated_at__date=today,
    )

    context = {
        "today": today,
        "today_check_ins": today_check_ins,
        "today_check_outs": today_check_outs,
        "reservations_made": reservations_made,
        "cancelled_bookings": cancelled_bookings,
        "maintenance_rooms": maintenance_rooms,
        "cleaning_rooms": cleaning_rooms,
        "today_event_bookings": today_event_bookings,
        "cancelled_event_bookings": cancelled_event_bookings,
    }
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
