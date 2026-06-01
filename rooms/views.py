from datetime import date

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import group_required
from bookings.models import Booking
from rooms.forms import RoomForm
from rooms.models import Room


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
            check_in_date = date.fromisoformat(check_in)
            check_out_date = date.fromisoformat(check_out)
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
            check_in__lt=check_out,
            check_out__gt=check_in,
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
