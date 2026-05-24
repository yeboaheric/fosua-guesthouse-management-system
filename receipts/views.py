from io import BytesIO

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from accounts.decorators import group_required
from bookings.models import Booking
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


@group_required("Admin", "Receptionist")
def booking_receipt_preview(request, booking_id):
    booking = get_object_or_404(Booking.objects.select_related("guest", "room"), pk=booking_id)
    return render(
        request,
        "receipts/booking_receipt.html",
        {
            "booking": booking,
            "guesthouse_name": "Fosua Guesthouse - Aduman",
        },
    )


@group_required("Admin", "Receptionist")
def booking_receipt_pdf(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related("guest", "room").prefetch_related("payments"),
        pk=booking_id,
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
    pdf.drawRightString(width - 18 * mm, y, f"Date: {booking.created_at:%Y-%m-%d %H:%M}")

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
    pdf.drawString(18 * mm, y, "Booking Information")
    y -= 6 * mm
    pdf.setFont("Helvetica", 10)
    pdf.drawString(18 * mm, y, f"Room: {booking.room.room_number} ({booking.room.get_room_type_display()})")
    y -= 5 * mm
    pdf.drawString(18 * mm, y, f"Check-In: {booking.check_in}")
    y -= 5 * mm
    pdf.drawString(18 * mm, y, f"Check-Out: {booking.check_out}")
    y -= 5 * mm
    pdf.drawString(18 * mm, y, f"Status: {booking.get_status_display()}")

    y -= 12 * mm
    pdf.setStrokeColor(colors.HexColor("#d9d9d9"))
    pdf.line(18 * mm, y, width - 18 * mm, y)
    y -= 8 * mm

    pdf.setFont("Helvetica", 10)
    pdf.drawString(18 * mm, y, "Total Booking Amount")
    pdf.drawRightString(width - 18 * mm, y, f"GHS {booking.total_amount}")
    y -= 6 * mm
    pdf.drawString(18 * mm, y, "Amount Paid")
    pdf.drawRightString(width - 18 * mm, y, f"GHS {booking.amount_paid}")
    y -= 6 * mm
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(18 * mm, y, "Balance Due")
    pdf.drawRightString(width - 18 * mm, y, f"GHS {booking.balance_due}")

    y -= 14 * mm
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(colors.HexColor("#555555"))
    pdf.drawString(18 * mm, y, "Thank you for choosing Fosua Guesthouse.")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    pdf_data = buffer.getvalue()

    filename = f"receipt-booking-{booking.id}.pdf"
    response = HttpResponse(pdf_data, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
