from calendar import monthrange
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from bookings.models import Booking, EventBooking, EventPayment, Payment
from inventory.models import Sale

MONEY_FIELD = DecimalField(max_digits=12, decimal_places=2)
ZERO_MONEY = Value(Decimal("0.00"), output_field=MONEY_FIELD)

BOOKING_REVENUE_STATUSES = (
    Booking.BookingStatus.CONFIRMED,
    Booking.BookingStatus.CHECKED_IN,
    Booking.BookingStatus.CHECKED_OUT,
)
EVENT_REVENUE_STATUSES = (
    EventBooking.EventBookingStatus.CONFIRMED,
    EventBooking.EventBookingStatus.IN_PROGRESS,
    EventBooking.EventBookingStatus.COMPLETED,
)


def normalize_date_range(start_date, end_date):
    if start_date <= end_date:
        return start_date, end_date
    return end_date, start_date


def report_window_for_period(period, today=None):
    today = today or timezone.localdate()
    if period == "daily":
        return today, today
    if period == "monthly":
        month_start = today.replace(day=1)
        month_end = today.replace(day=monthrange(today.year, today.month)[1])
        return month_start, month_end
    if period == "yearly":
        return today.replace(month=1, day=1), today.replace(month=12, day=31)
    week_start = today - timedelta(days=today.weekday())
    return week_start, week_start + timedelta(days=6)


def local_datetime_range(start_date, end_date):
    start_date, end_date = normalize_date_range(start_date, end_date)
    local_tz = timezone.get_current_timezone()
    start_at = timezone.make_aware(datetime.combine(start_date, time.min), local_tz)
    end_at = timezone.make_aware(datetime.combine(end_date, time.max), local_tz)
    return start_at, end_at


def filter_queryset_for_local_datetime_range(queryset, field_name, start_date, end_date):
    start_at, end_at = local_datetime_range(start_date, end_date)
    return queryset.filter(**{f"{field_name}__gte": start_at, f"{field_name}__lte": end_at})


def money_total(queryset, field_name):
    return queryset.aggregate(
        total=Coalesce(
            Sum(field_name),
            ZERO_MONEY,
        )
    )["total"]


def booking_revenue_queryset(start_date, end_date, room_type=""):
    start_date, end_date = normalize_date_range(start_date, end_date)
    queryset = Booking.objects.filter(
        status__in=BOOKING_REVENUE_STATUSES,
        check_in__range=[start_date, end_date],
    )
    if room_type:
        queryset = queryset.filter(room__room_type=room_type)
    return queryset


def booking_payment_queryset(start_date, end_date, room_type=""):
    queryset = filter_queryset_for_local_datetime_range(Payment.objects.all(), "paid_at", start_date, end_date)
    if room_type:
        queryset = queryset.filter(booking__room__room_type=room_type)
    return queryset


def event_revenue_queryset(start_date, end_date):
    return filter_queryset_for_local_datetime_range(
        EventBooking.objects.filter(status__in=EVENT_REVENUE_STATUSES),
        "event_start",
        start_date,
        end_date,
    )


def event_payment_queryset(start_date, end_date):
    return filter_queryset_for_local_datetime_range(EventPayment.objects.all(), "paid_at", start_date, end_date)


def completed_pos_sales_queryset(start_date, end_date):
    return filter_queryset_for_local_datetime_range(
        Sale.objects.filter(status=Sale.SaleStatus.COMPLETED),
        "created_at",
        start_date,
        end_date,
    )


def booking_revenue_total(start_date, end_date, room_type=""):
    return money_total(booking_revenue_queryset(start_date, end_date, room_type), "total_amount")


def event_revenue_total(start_date, end_date):
    return money_total(event_revenue_queryset(start_date, end_date), "total_amount")


def pos_sales_total(start_date, end_date):
    return money_total(completed_pos_sales_queryset(start_date, end_date), "grand_total")


def payments_received_total(start_date, end_date, room_type=""):
    return money_total(booking_payment_queryset(start_date, end_date, room_type), "amount") + money_total(
        event_payment_queryset(start_date, end_date),
        "amount",
    )


def revenue_components(start_date, end_date, room_type=""):
    booking_total = booking_revenue_total(start_date, end_date, room_type)
    event_total = event_revenue_total(start_date, end_date)
    pos_total = pos_sales_total(start_date, end_date)
    return {
        "booking_revenue": booking_total,
        "event_revenue": event_total,
        "pos_sales": pos_total,
        "payments_received": payments_received_total(start_date, end_date, room_type),
        "total_revenue": booking_total + event_total + pos_total,
    }


def _daily_money_map_from_date_queryset(queryset, date_field, amount_field):
    rows = (
        queryset.values(date_field)
        .annotate(total=Coalesce(Sum(amount_field), ZERO_MONEY))
        .order_by(date_field)
    )
    return {row[date_field]: Decimal(str(row["total"] or 0)) for row in rows}


def _daily_money_map_from_datetime_queryset(queryset, datetime_field, amount_field):
    rows = (
        queryset.annotate(day=TruncDate(datetime_field))
        .values("day")
        .annotate(total=Coalesce(Sum(amount_field), ZERO_MONEY))
        .order_by("day")
    )
    return {row["day"]: Decimal(str(row["total"] or 0)) for row in rows}


def daily_booking_revenue_map(start_date, end_date, room_type=""):
    return _daily_money_map_from_date_queryset(
        booking_revenue_queryset(start_date, end_date, room_type),
        "check_in",
        "total_amount",
    )


def daily_total_revenue_map(start_date, end_date, room_type=""):
    booking_map = daily_booking_revenue_map(start_date, end_date, room_type)
    event_map = _daily_money_map_from_datetime_queryset(
        event_revenue_queryset(start_date, end_date),
        "event_start",
        "total_amount",
    )
    pos_map = _daily_money_map_from_datetime_queryset(
        completed_pos_sales_queryset(start_date, end_date),
        "created_at",
        "grand_total",
    )
    current_day = min(start_date, end_date)
    final_day = max(start_date, end_date)
    totals = {}
    while current_day <= final_day:
        totals[current_day] = (
            booking_map.get(current_day, Decimal("0"))
            + event_map.get(current_day, Decimal("0"))
            + pos_map.get(current_day, Decimal("0"))
        )
        current_day += timedelta(days=1)
    return totals
