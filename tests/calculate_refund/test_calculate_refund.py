"""Refund rules, boundaries, validation, and injected source behavior."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.booking import BookingNotFound
from app.tools.calculate_refund import (
    BookingStatusNotConfirmed,
    CalculateRefundResult,
    calculate_refund,
)


@pytest.mark.parametrize(
    ("before_start", "rental_refund", "rule"),
    [
        (timedelta(hours=73), "40", "at_least_48_hours"),
        (timedelta(hours=48), "40", "at_least_48_hours"),
        (timedelta(hours=48) - timedelta(seconds=1), "20", "24_to_48_hours"),
        (timedelta(hours=24), "20", "24_to_48_hours"),
        (timedelta(hours=24) - timedelta(seconds=1), "0", "less_than_24_hours"),
        (timedelta(0), "0", "less_than_24_hours"),
        (-timedelta(seconds=1), "0", "less_than_24_hours"),
    ],
)
def test_refund_tiers(booking_data, before_start, rental_refund, rule):
    booking = booking_data["CW-1001"]
    result = calculate_refund(
        booking.id,
        cancellation_time=booking.start - before_start,
        booking_loader=lambda: booking_data,
    )
    assert isinstance(result, CalculateRefundResult)
    assert result.rental_refund == Decimal(rental_refund)
    assert result.deposit_refund == Decimal("50")
    assert result.refund == Decimal(rental_refund) + Decimal("50")
    assert result.booking_fee_refund == Decimal("0")
    assert result.booking_fee_retained == Decimal("2")
    assert result.rule == rule
    assert result.paid_with == "card"


@pytest.mark.parametrize(
    ("booking_id", "expected"),
    [("CW-1001", "90"), ("CW-1002", "340"), ("CW-1003", "50"),
     ("CW-1007", "186"), ("CW-1010", "170")],
)
def test_fixed_assignment_time(booking_data, booking_id, expected):
    result = calculate_refund(booking_id, booking_loader=lambda: booking_data)
    assert isinstance(result, CalculateRefundResult)
    assert result.refund == Decimal(expected)


@pytest.mark.parametrize("booking_id", ["CW-1005", "CW-1006", "CW-1008"])
def test_non_confirmed_bookings(booking_data, booking_id):
    booking = booking_data[booking_id]
    result = calculate_refund(
        booking.id,
        cancellation_time=booking.start - timedelta(hours=48),
        booking_loader=lambda: booking_data,
    )
    assert isinstance(result, BookingStatusNotConfirmed)
    assert result.id == booking_id
    assert booking.status.value in result.message


def test_voucher_refund(booking_data):
    result = calculate_refund("CW-1004", booking_loader=lambda: booking_data)
    assert isinstance(result, CalculateRefundResult)
    assert result.refund == Decimal("73")
    assert result.rental_refund == Decimal("23")
    assert result.deposit_refund == Decimal("50")
    assert result.paid_with == "voucher"
    assert result.deposit_refund_method == "original_payment_method"


def test_unknown_booking():
    result = calculate_refund("CW-9999", booking_loader=lambda: {})
    assert isinstance(result, BookingNotFound)
    assert result.id == "CW-9999"
    assert result.result == "not_found"


@pytest.mark.parametrize("invalid_time", [0.0, "2026-06-10T09:00:00+02:00", None])
def test_invalid_time_type(invalid_time):
    with pytest.raises(TypeError, match="must be a datetime"):
        calculate_refund("CW-1001", cancellation_time=invalid_time, booking_loader=lambda: {})


def test_naive_time_is_rejected():
    with pytest.raises(ValueError, match="must be timezone-aware"):
        calculate_refund(
            "CW-1001", cancellation_time=datetime(2026, 6, 10, 9),
            booking_loader=lambda: {},
        )


def test_equivalent_timezones(booking_data):
    booking = booking_data["CW-1001"]
    local_time = booking.start - timedelta(hours=48)
    local_result = calculate_refund(
        booking.id, cancellation_time=local_time, booking_loader=lambda: booking_data,
    )
    utc_result = calculate_refund(
        booking.id, cancellation_time=local_time.astimezone(timezone.utc),
        booking_loader=lambda: booking_data,
    )
    assert local_result == utc_result


def test_source_error_propagates():
    def failing_loader():
        raise OSError("Booking source unavailable")

    with pytest.raises(OSError, match="Booking source unavailable"):
        calculate_refund("CW-1001", booking_loader=failing_loader)
