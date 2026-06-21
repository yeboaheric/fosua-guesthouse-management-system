from io import BytesIO

from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from accounts.decorators import group_required
from bookings.models import Booking
from bookings.models import Payment
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


@group_required("Admin", "Receptionist", module="reservations", action="print")
def booking_receipt_preview(request, booking_id):
    booking = get_object_or_404(Booking.objects.select_related("guest", "room"), pk=booking_id)
    related_bookings = _grouped_bookings(booking)
    payments = Payment.objects.filter(booking__in=related_bookings).select_related(
        "received_by", "booking__room"
    )
    return render(
        request,
        "receipts/booking_receipt.html",
        {
            "booking": booking,
            "related_bookings": related_bookings,
            "payments": payments,
            "group_total": sum(item.total_amount for item in related_bookings),
            "group_paid": sum(item.amount_paid for item in related_bookings),
            "group_balance": sum(item.balance_due for item in related_bookings),
            "guesthouse_name": "Fosua Guesthouse - Aduman",
        },
    )


@group_required("Admin", "Receptionist", module="reservations", action="print")
def booking_receipt_pdf(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related("guest", "room").prefetch_related("payments"),
        pk=booking_id,
    )
    pdf_data = _render_booking_receipt_pdf(booking)
    filename = f"receipt-booking-{booking.id}.pdf"
    response = HttpResponse(pdf_data, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@require_POST
@group_required("Admin", "Receptionist", module="reservations", action="print")
def booking_receipt_email(request, booking_id):
    booking = get_object_or_404(Booking.objects.select_related("guest", "room"), pk=booking_id)
    if not booking.guest.email:
        messages.error(request, "This guest does not have an email address on file.")
        return redirect("receipt-preview", booking_id=booking.pk)

    email = EmailMessage(
        subject=f"Fosua Guesthouse Receipt BK-{booking.pk}",
        body=(
            f"Dear {booking.guest.first_name},\n\n"
            "Please find your booking receipt attached from Fosua Guesthouse - Aduman.\n"
        ),
        to=[booking.guest.email],
    )
    email.attach(
        f"receipt-booking-{booking.pk}.pdf",
        _render_booking_receipt_pdf(booking),
        "application/pdf",
    )
    email.send(fail_silently=False)
    messages.success(request, f"Receipt sent to {booking.guest.email}.")
    return redirect("receipt-preview", booking_id=booking.pk)


def _grouped_bookings(booking):
    return list(
        Booking.objects.select_related("guest", "room")
        .filter(guest=booking.guest, check_in=booking.check_in, check_out=booking.check_out)
        .order_by("room__room_number", "created_at")
    )


def _render_booking_receipt_pdf(booking):
    related_bookings = _grouped_bookings(booking)
    payments = Payment.objects.filter(booking__in=related_bookings).select_related(
        "received_by", "booking__room"
    )

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.setFillColor(colors.HexColor("#23444b"))
    pdf.rect(0, height - 35 * mm, width, 35 * mm, stroke=0, fill=1)

    pdf.setFillColor(colors.HexColor("#f7faf9"))
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(18 * mm, height - 20 * mm, "Fosua Guesthouse - Aduman")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(18 * mm, height - 26 * mm, "Official Booking Receipt")

    y = height - 45 * mm
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(18 * mm, y, f"Receipt #: BK-{booking.id}")
    pdf.drawRightString(width - 18 * mm, y, f"Booked: {booking.created_at:%Y-%m-%d %H:%M}")

    y -= 10 * mm
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(18 * mm, y, "Guest Information")
    y -= 6 * mm
    pdf.setFont("Helvetica", 10)
    pdf.drawString(18 * mm, y, f"Name: {booking.guest.first_name} {booking.guest.last_name}")
    y -= 5 * mm
    pdf.drawString(18 * mm, y, f"Phone: {booking.guest.phone_number}")
    y -= 5 * mm
    pdf.drawString(18 * mm, y, f"Email: {booking.guest.email or '-'}")

    y -= 10 * mm
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(18 * mm, y, "Booked Rooms")
    y -= 6 * mm
    pdf.setFont("Helvetica", 10)
    for room_booking in related_bookings:
        pdf.drawString(
            18 * mm,
            y,
            f"Room {room_booking.room.room_number} ({room_booking.room.get_room_type_display()}) "
            f"{room_booking.check_in} to {room_booking.check_out} - {room_booking.get_status_display()}",
        )
        y -= 5 * mm

    y -= 4 * mm
    pdf.setStrokeColor(colors.HexColor("#d9d9d9"))
    pdf.line(18 * mm, y, width - 18 * mm, y)
    y -= 8 * mm

    pdf.setFont("Helvetica", 10)
    pdf.drawString(18 * mm, y, "Total Booking Amount")
    pdf.drawRightString(
        width - 18 * mm,
        y,
        f"GHS {sum(item.total_amount for item in related_bookings)}",
    )
    y -= 6 * mm
    pdf.drawString(18 * mm, y, "Amount Paid")
    pdf.drawRightString(
        width - 18 * mm,
        y,
        f"GHS {sum(item.amount_paid for item in related_bookings)}",
    )
    y -= 6 * mm
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(18 * mm, y, "Balance Due")
    pdf.drawRightString(
        width - 18 * mm,
        y,
        f"GHS {sum(item.balance_due for item in related_bookings)}",
    )

    y -= 12 * mm
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(18 * mm, y, "Payments")
    y -= 6 * mm
    pdf.setFont("Helvetica", 9)
    if payments:
        for payment in payments:
            pdf.drawString(
                18 * mm,
                y,
                f"{payment.paid_at:%Y-%m-%d %H:%M} - Room {payment.booking.room.room_number} - "
                f"{payment.get_method_display()} - GHS {payment.amount}",
            )
            y -= 5 * mm
            if y < 20 * mm:
                pdf.showPage()
                y = height - 20 * mm
                pdf.setFont("Helvetica", 9)
    else:
        pdf.drawString(18 * mm, y, "No payments recorded yet.")

    y -= 10 * mm
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(colors.HexColor("#555555"))
    pdf.drawString(18 * mm, y, "Thank you for choosing Fosua Guesthouse.")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()
