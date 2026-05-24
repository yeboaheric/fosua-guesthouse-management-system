from django.urls import path

from receipts.views import booking_receipt_pdf, booking_receipt_preview

urlpatterns = [
    path("booking/<int:booking_id>/", booking_receipt_preview, name="receipt-preview"),
    path("booking/<int:booking_id>/pdf/", booking_receipt_pdf, name="receipt-pdf"),
]
