from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import group_required
from guests.forms import GuestForm
from guests.models import Guest


@group_required("Admin", "Receptionist")
def guest_list(request):
    guests = Guest.objects.all()
    return render(request, "guests/guest_list.html", {"guests": guests})


@group_required("Admin", "Receptionist")
def guest_create(request):
    if request.method == "POST":
        form = GuestForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Guest created successfully.")
            return redirect("guest-list")
    else:
        form = GuestForm()
    return render(request, "guests/guest_form.html", {"form": form, "title": "Add Guest"})


@group_required("Admin", "Receptionist")
def guest_update(request, pk):
    guest = get_object_or_404(Guest, pk=pk)
    if request.method == "POST":
        form = GuestForm(request.POST, instance=guest)
        if form.is_valid():
            form.save()
            messages.success(request, "Guest updated successfully.")
            return redirect("guest-list")
    else:
        form = GuestForm(instance=guest)
    return render(request, "guests/guest_form.html", {"form": form, "title": "Edit Guest"})
