from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import group_required
from guests.forms import GuestForm
from guests.models import Guest


@group_required("Admin", "Receptionist", module="guests")
def guest_list(request):
    query = request.GET.get("q", "").strip()
    guests = Guest.objects.all()
    if query:
        guests = guests.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(phone_number__icontains=query)
            | Q(email__icontains=query)
            | Q(ghana_card_number__icontains=query)
            | Q(digital_address__icontains=query)
        )
    return render(request, "guests/guest_list.html", {"guests": guests, "query": query})


@group_required("Admin", "Receptionist", module="guests", action="create")
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


@group_required("Admin", "Receptionist", module="guests", action="edit")
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
