"""Deterministic cancellation quotes; no booking changes or money transfers."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.db.booking_loader import BookingLoader, load_booking
from app.models.booking import BookingNotFound, BookingStatus, Money


ASSIGNMENT_NOW = datetime.fromisoformat("2026-06-10T09:00:00+02:00")


class CalculateRefundResult(BaseModel):
    refund: Money
    rental_refund: Money
    deposit_refund: Money
    booking_fee_refund: Money = Decimal("0")
    booking_fee_retained: Money
    rule: Literal["at_least_48_hours", "24_to_48_hours", "less_than_24_hours"]
    paid_with: Literal["card", "voucher"]
    deposit_refund_method: Literal["original_payment_method"] = "original_payment_method"


class BookingStatusNotConfirmed(BaseModel):
    id: str
    message: str


def calculate_refund(
    booking_id: str,
    *,
    cancellation_time: datetime = ASSIGNMENT_NOW,
    booking_loader: BookingLoader = load_booking,
) -> CalculateRefundResult | BookingNotFound | BookingStatusNotConfirmed:
    """Quote a refund using the fixed assignment time unless explicitly supplied.

    Only confirmed bookings are eligible. A confirmed booking whose start has
    passed follows the less-than-24-hours rule; its status is not inferred.
    paid_with describes the rental payment; the deposit follows its own original
    payment method, which is not separately recorded in the supplied data.
    """
    if not isinstance(cancellation_time, datetime):
        raise TypeError("cancellation_time must be a datetime")
    if cancellation_time.tzinfo is None or cancellation_time.utcoffset() is None:
        raise ValueError("cancellation_time must be timezone-aware")

    bookings = booking_loader()
    booking = bookings.get(booking_id)
    if booking is None:
        return BookingNotFound(
            id=booking_id,
            message=f"Booking {booking_id} not found",
        )
    if booking.status != BookingStatus.CONFIRMED:
        return BookingStatusNotConfirmed(
            id=booking_id,
            message=f"Booking {booking_id} with status {booking.status.value} cannot be cancelled or refunded",
        )

    # Compare elapsed time in UTC so differing offsets and DST do not change tiers.
    time_until_start = booking.start.astimezone(timezone.utc) - cancellation_time.astimezone(timezone.utc)
    if time_until_start >= timedelta(hours=48):
        rental_refund = booking.rental_price_eur
        rule = "at_least_48_hours"
    elif time_until_start >= timedelta(hours=24):
        rental_refund = booking.rental_price_eur / Decimal("2")
        rule = "24_to_48_hours"
    else:
        rental_refund = Decimal("0")
        rule = "less_than_24_hours"

    return CalculateRefundResult(
        refund=booking.deposit_eur + rental_refund,
        rental_refund=rental_refund,
        deposit_refund=booking.deposit_eur,
        booking_fee_retained=booking.booking_fee_eur,
        rule=rule,
        paid_with=booking.paid_with,
    )
