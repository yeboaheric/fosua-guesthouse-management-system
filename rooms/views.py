from datetime import date

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import group_required
from bookings.models import Booking
from rooms.forms import RoomForm
from rooms.models import Room
from rooms.forms import (
    HousekeepingStatusForm,
    HousekeepingTaskForm,
    InspectionForm,
)
from rooms.models import (
    HousekeepingHistory,
    HousekeepingTask,
    InspectionRecord,
)
from rooms.models import HousekeepingTaskToiletry
from django.forms import inlineformset_factory
from django.contrib.auth import get_user_model
User = get_user_model()


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


@group_required("Admin", "Receptionist", "Housekeeping", module="housekeeping")
def housekeeping_dashboard(request):
    rooms = Room.objects.order_by("room_number")
    tasks = HousekeepingTask.objects.order_by("-created_at")[:10]
    recent_history = HousekeepingHistory.objects.select_related("changed_by", "room").all()[:10]
    pending_tasks = HousekeepingTask.objects.filter(status=HousekeepingTask.TaskStatus.PENDING).count()
    overdue_tasks = HousekeepingTask.objects.filter(status=HousekeepingTask.TaskStatus.OVERDUE).count()
    context = {
        "rooms": rooms,
        "tasks": tasks,
        "recent_history": recent_history,
        "pending_tasks": pending_tasks,
        "overdue_tasks": overdue_tasks,
    }
    return render(request, "rooms/housekeeping_dashboard.html", context)


@group_required("Admin", "Receptionist", "Housekeeping", module="housekeeping")
def housekeeping_update_status(request, pk=None):
    if pk:
        room = get_object_or_404(Room, pk=pk)
    else:
        room = None
    if request.method == "POST":
        form = HousekeepingStatusForm(request.POST)
        if form.is_valid():
            room = form.cleaned_data["room"]
            new_status = form.cleaned_data["new_status"]
            notes = form.cleaned_data.get("notes", "")
            previous = room.housekeeping_status
            room.housekeeping_status = new_status
            room.housekeeping_last_changed_at = timezone.now()
            room.save()
            HousekeepingHistory.objects.create(
                room=room,
                previous_status=previous,
                new_status=new_status,
                changed_by=request.user,
                notes=notes,
            )
            messages.success(request, "Housekeeping status updated.")
            return redirect("housekeeping-dashboard")
    else:
        initial = {"room": room} if room else {}
        form = HousekeepingStatusForm(initial=initial)
    return render(request, "rooms/housekeeping_status_form.html", {"form": form, "room": room})


@group_required("Admin", "Receptionist", "Housekeeping", module="housekeeping")
def housekeeping_task_list(request):
    tasks = HousekeepingTask.objects.select_related("room", "assigned_to").order_by("-created_at")
    return render(request, "rooms/housekeeping_task_list.html", {"tasks": tasks})


@group_required("Admin", "Receptionist", "Housekeeping", module="housekeeping")
def housekeeping_task_create(request):
    if request.method == "POST":
        form = HousekeepingTaskForm(request.POST)
        TaskToiletryFormSet = inlineformset_factory(HousekeepingTask, HousekeepingTaskToiletry, fields=("item", "quantity"), extra=1, can_delete=True)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.save()
            formset = TaskToiletryFormSet(request.POST, instance=task)
            if formset.is_valid():
                formset.save()
            messages.success(request, "Housekeeping task created.")
            return redirect("housekeeping-tasks")
    else:
        form = HousekeepingTaskForm()
        TaskToiletryFormSet = inlineformset_factory(HousekeepingTask, HousekeepingTaskToiletry, fields=("item", "quantity"), extra=1, can_delete=True)
        formset = TaskToiletryFormSet()
    return render(request, "rooms/housekeeping_task_form.html", {"form": form, "formset": formset})


@group_required("Admin", "Receptionist", "Housekeeping", module="housekeeping")
def housekeeping_task_update(request, pk):
    task = get_object_or_404(HousekeepingTask, pk=pk)
    if request.method == "POST":
        form = HousekeepingTaskForm(request.POST, instance=task)
        TaskToiletryFormSet = inlineformset_factory(HousekeepingTask, HousekeepingTaskToiletry, fields=("item", "quantity"), extra=1, can_delete=True)
        formset = TaskToiletryFormSet(request.POST, instance=task)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, "Housekeeping task updated.")
            return redirect("housekeeping-tasks")
    else:
        form = HousekeepingTaskForm(instance=task)
        TaskToiletryFormSet = inlineformset_factory(HousekeepingTask, HousekeepingTaskToiletry, fields=("item", "quantity"), extra=1, can_delete=True)
        formset = TaskToiletryFormSet(instance=task)
    return render(request, "rooms/housekeeping_task_form.html", {"form": form, "task": task, "formset": formset})


@group_required("Admin", "Receptionist", "Housekeeping", module="housekeeping")
def housekeeping_task_complete(request, pk):
    task = get_object_or_404(HousekeepingTask, pk=pk)
    task.status = HousekeepingTask.TaskStatus.COMPLETED
    task.completed_at = timezone.now()
    task.save()
    # Issue any required toiletries linked to this task and decrement stock
    try:
        from inventory.models import ToiletryIssue
    except Exception:
        ToiletryIssue = None

    if ToiletryIssue:
        for req in task.toiletry_requirements.select_related("item").all():
            item = req.item
            qty = req.quantity
            issued_qty = min(item.quantity_in_stock, qty)
            if issued_qty > 0:
                # decrement stock
                item.quantity_in_stock = item.quantity_in_stock - issued_qty
                item.save()
                ToiletryIssue.objects.create(
                    item=item,
                    room=task.room,
                    issued_by=task.assigned_to or task.created_by,
                    quantity=issued_qty,
                    reason=f"Replenishment for task {task.title}",
                )
            else:
                messages.warning(request, f"Not enough stock for {item.name} to fulfill replenishment.")

    messages.success(request, "Housekeeping task marked completed.")
    return redirect("housekeeping-tasks")


@group_required("Admin", "Receptionist", "Housekeeping", module="housekeeping")
def housekeeping_history(request, room_pk=None):
    history = HousekeepingHistory.objects.select_related("room", "changed_by").order_by("-created_at")
    if room_pk:
        history = history.filter(room_id=room_pk)
    return render(request, "rooms/housekeeping_history.html", {"history": history})
