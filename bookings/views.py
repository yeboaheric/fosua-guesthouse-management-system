from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import group_required
from bookings.forms import BookingForm
from bookings.forms import PaymentForm
from bookings.models import Booking, Payment
from rooms.models import Room


@group_required("Admin", "Receptionist")
def booking_list(request):
    bookings = Booking.objects.select_related("guest", "room", "created_by").annotate(
        paid_total=Coalesce(
            Sum("payments__amount"),
            Value(0, output_field=DecimalField(max_digits=10, decimal_places=2)),
        )
    )
    status = request.GET.get("status")
    if status:
        bookings = bookings.filter(status=status)
    return render(
        request,
        "bookings/booking_list.html",
        {"bookings": bookings, "status_choices": Booking.BookingStatus.choices},
    )


@group_required("Admin", "Receptionist")
def booking_create(request):
    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.created_by = request.user
            try:
                booking.save()
            except ValidationError as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, "Booking created successfully.")
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


@group_required("Admin", "Receptionist")
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


@require_POST
@group_required("Admin", "Receptionist")
def booking_confirm(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if booking.status == Booking.BookingStatus.PENDING:
        booking.status = Booking.BookingStatus.CONFIRMED
        booking.save(update_fields=["status", "updated_at"])
        messages.success(request, "Booking confirmed.")
    return redirect("booking-list")


@require_POST
@group_required("Admin", "Receptionist")
def booking_check_in(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if booking.status in [Booking.BookingStatus.CONFIRMED, Booking.BookingStatus.PENDING]:
        booking.status = Booking.BookingStatus.CHECKED_IN
        booking.save(update_fields=["status", "updated_at"])
        Room.objects.filter(pk=booking.room_id).update(status=Room.RoomStatus.OCCUPIED)
        messages.success(request, "Guest checked in.")
    return redirect("booking-list")


@require_POST
@group_required("Admin", "Receptionist")
def booking_check_out(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if booking.status == Booking.BookingStatus.CHECKED_IN:
        booking.status = Booking.BookingStatus.CHECKED_OUT
        booking.save(update_fields=["status", "updated_at"])
        Room.objects.filter(pk=booking.room_id).update(status=Room.RoomStatus.AVAILABLE)
        messages.success(request, "Guest checked out.")
    return redirect("booking-list")


@require_POST
@group_required("Admin", "Receptionist")
def booking_cancel(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if booking.status in [Booking.BookingStatus.PENDING, Booking.BookingStatus.CONFIRMED]:
        booking.status = Booking.BookingStatus.CANCELLED
        booking.save(update_fields=["status", "updated_at"])
        messages.success(request, "Booking cancelled.")
    return redirect("booking-list")


@group_required("Admin", "Receptionist")
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
        },
    )


@group_required("Admin", "Receptionist")
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

    context = {
        "today": today,
        "today_check_ins": today_check_ins,
        "today_check_outs": today_check_outs,
        "reservations_made": reservations_made,
        "cancelled_bookings": cancelled_bookings,
        "maintenance_rooms": maintenance_rooms,
        "cleaning_rooms": cleaning_rooms,
    }
    return render(request, "bookings/operations_overview.html", context)
