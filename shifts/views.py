from datetime import timedelta

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import group_required
from bookings.models import Booking
from rooms.models import Room
from shifts.forms import ShiftHandoverForm, ShiftHandoverUpdateForm
from shifts.models import ShiftHandover
from shifts.models import ShiftHandoverUpdate


@group_required("Admin", "Receptionist", module="handovers")
def handover_list(request):
    handovers = ShiftHandover.objects.select_related("prepared_by")
    return render(request, "shifts/handover_list.html", {"handovers": handovers})


@group_required("Admin", "Receptionist", module="handovers")
def handover_create(request):
    if request.method == "POST":
        form = ShiftHandoverForm(request.POST)
        if form.is_valid():
            handover = form.save(commit=False)
            handover.prepared_by = request.user
            _populate_shift_metrics(handover)
            handover.save()
            messages.success(request, "Shift handover report created.")
            return redirect("handover-detail", pk=handover.pk)
    else:
        now = timezone.localtime()
        default_start = now.replace(minute=0, second=0, microsecond=0)
        form = ShiftHandoverForm(
            initial={
                "started_at": (default_start - timedelta(hours=8)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "ended_at": default_start.strftime("%Y-%m-%dT%H:%M"),
            }
        )
    return render(
        request,
        "shifts/handover_form.html",
        {"form": form, "title": "End Shift and Create Handover"},
    )


@group_required("Admin", "Receptionist", module="handovers")
def handover_detail(request, pk):
    handover = get_object_or_404(
        ShiftHandover.objects.select_related("prepared_by").prefetch_related("updates__author"),
        pk=pk,
    )
    if request.method == "POST":
        update_form = ShiftHandoverUpdateForm(request.POST)
        if update_form.is_valid():
            update = update_form.save(commit=False)
            update.handover = handover
            update.author = request.user
            update.save()
            messages.success(request, "Handover update added.")
            return redirect("handover-detail", pk=handover.pk)
    else:
        update_form = ShiftHandoverUpdateForm()

    return render(
        request,
        "shifts/handover_detail.html",
        {
            "handover": handover,
            "update_form": update_form,
            "updates": handover.updates.select_related("author"),
        },
    )


def _populate_shift_metrics(handover):
    start = handover.started_at
    end = handover.ended_at
    start_date = timezone.localtime(start).date()
    end_date = timezone.localtime(end).date()

    handover.check_ins_count = Booking.objects.filter(check_in__range=[start_date, end_date]).count()
    handover.check_outs_count = Booking.objects.filter(
        check_out__range=[start_date, end_date]
    ).count()
    handover.reservations_count = Booking.objects.filter(created_at__range=[start, end]).count()
    handover.cancellations_count = Booking.objects.filter(
        status=Booking.BookingStatus.CANCELLED,
        updated_at__range=[start, end],
    ).count()
    handover.maintenance_rooms_count = Room.objects.filter(
        status=Room.RoomStatus.MAINTENANCE
    ).count()
    handover.cleaning_rooms_count = Room.objects.filter(status=Room.RoomStatus.CLEANING).count()
