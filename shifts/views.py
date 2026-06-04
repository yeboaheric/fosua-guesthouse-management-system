from collections import OrderedDict
from datetime import timedelta

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db.models import Q

from accounts.decorators import group_required
from bookings.models import Booking
from rooms.models import Room
from shifts.forms import ShiftHandoverForm, ShiftHandoverUpdateForm, RosterFilterForm
from shifts.models import ShiftHandover, ShiftHandoverUpdate, DutyRoster, DutyRosterEntry, Shift, Department
from django.contrib.auth import get_user_model

User = get_user_model()


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


@group_required("Admin", "Manager", module="handovers")
def roster_report(request):
    """List and filter duty rosters for reporting and export."""
    form = RosterFilterForm(request.GET)
    rosters = DutyRoster.objects.select_related("created_by").prefetch_related("entries__employee", "entries__department", "entries__shift")

    if form.is_valid():
        start_date = form.cleaned_data.get("start_date")
        end_date = form.cleaned_data.get("end_date")
        department = form.cleaned_data.get("department")
        shift = form.cleaned_data.get("shift")
        employee = form.cleaned_data.get("employee")
        role = form.cleaned_data.get("role")
        status = form.cleaned_data.get("status")

        if start_date:
            rosters = rosters.filter(roster_date__gte=start_date)
        if end_date:
            rosters = rosters.filter(roster_date__lte=end_date)

        if department or shift or employee or role or status:
            entries = DutyRosterEntry.objects.select_related("roster")
            if department:
                entries = entries.filter(department=department)
            if shift:
                entries = entries.filter(shift=shift)
            if employee:
                entries = entries.filter(employee=employee)
            if role:
                entries = entries.filter(role__icontains=role)
            if status:
                entries = entries.filter(status=status)
            roster_ids = entries.values_list("roster_id", flat=True).distinct()
            rosters = rosters.filter(id__in=roster_ids)

    rosters = rosters.order_by("-roster_date")

    context = {
        "form": form,
        "filter_form": form,
        "rosters": rosters,
    }
    return render(request, "shifts/roster_report.html", context)


@group_required("Admin", "Manager", module="handovers")
def roster_detail(request, pk):
    """Display a detailed roster with all assignments."""
    roster = get_object_or_404(
        DutyRoster.objects.prefetch_related(
            "entries__employee",
            "entries__department",
            "entries__shift",
            "entries__assigned_by",
        ),
        pk=pk,
    )
    entries = roster.entries.select_related("employee", "department", "shift").order_by(
        "shift__start_time",
        "employee__first_name",
        "employee__last_name",
    )
    grouped_entries = OrderedDict()
    for entry in entries:
        grouped_entries.setdefault(entry.shift, []).append(entry)

    context = {
        "roster": roster,
        "entries": entries,
        "grouped_entries": grouped_entries.items(),
        "departments": Department.objects.filter(
            roster_entries__roster=roster,
            is_active=True,
        ).distinct().order_by("name"),
        "shifts": Shift.objects.filter(
            roster_entries__roster=roster,
            is_active=True,
        ).distinct().order_by("start_time"),
    }
    return render(request, "shifts/roster_detail.html", context)


@group_required("Admin", "Manager", module="handovers")
def roster_export_excel(request):
    """Export roster data to Excel."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    except ImportError:
        messages.error(request, "openpyxl is not installed. Please install it to export to Excel.")
        return redirect("roster-report")

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    department_id = request.GET.get("department")
    shift_id = request.GET.get("shift")
    employee_id = request.GET.get("employee")

    rosters = DutyRoster.objects.prefetch_related(
        "entries__employee",
        "entries__department",
        "entries__shift",
    )

    if start_date:
        from datetime import datetime
        rosters = rosters.filter(roster_date__gte=start_date)
    if end_date:
        from datetime import datetime
        rosters = rosters.filter(roster_date__lte=end_date)

    if department_id:
        rosters = rosters.filter(entries__department_id=department_id).distinct()
    if shift_id:
        rosters = rosters.filter(entries__shift_id=shift_id).distinct()
    if employee_id:
        rosters = rosters.filter(entries__employee_id=employee_id).distinct()

    rosters = rosters.order_by("roster_date")

    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Duty Roster"

    # Define styles
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    title_font = Font(bold=True, size=14)
    border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    # Headers begin on the first row so exports are straightforward to consume.
    row = 1
    headers = ["Date", "Shift", "Department", "Employee", "Role", "Assigned Duties", "Status"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border

    # Data
    row = 2
    for roster in rosters:
        for entry in roster.entries.select_related("employee", "department", "shift").order_by("shift__start_time"):
            ws.cell(row=row, column=1).value = roster.roster_date.strftime("%d/%m/%Y")
            ws.cell(row=row, column=2).value = entry.shift.name
            ws.cell(row=row, column=3).value = entry.department.name
            ws.cell(row=row, column=4).value = entry.employee.get_full_name()
            ws.cell(row=row, column=5).value = entry.role
            ws.cell(row=row, column=6).value = entry.assigned_duties
            ws.cell(row=row, column=7).value = entry.get_status_display()

            for col in range(1, 8):
                cell = ws.cell(row=row, column=col)
                cell.border = border
                cell.alignment = Alignment(vertical="top", wrap_text=True)

            row += 1

    # Adjust column widths
    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 15
    ws.column_dimensions["E"].width = 15
    ws.column_dimensions["F"].width = 30
    ws.column_dimensions["G"].width = 12

    # Generate response
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="roster_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    )
    wb.save(response)
    return response


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
