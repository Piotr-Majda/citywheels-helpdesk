"""Unit tests using explicitly injected booking data."""

import json
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.tools.get_booking import (
    BookingBase,
    BookingNotFound,
    BookingRead,
    get_booking,
    load_booking,
)


@pytest.fixture
def booking_payload():
    fixture_path = Path(__file__).with_name("fake_booking.json")
    return json.loads(fixture_path.read_text(encoding="utf-8"))[0]


@pytest.fixture
def booking_data(booking_payload):
    booking = BookingRead.model_validate(booking_payload)
    return {booking.id: booking}


def test_existing_booking(booking_data):
    result = get_booking("CW-1001", booking_loader=lambda: booking_data)
    assert isinstance(result, BookingRead)
    assert result.model_dump() == booking_data["CW-1001"].model_dump()
    assert result.rental_price_eur == Decimal("40")


def test_unknown_booking(booking_data):
    result = get_booking("CW-1023", booking_loader=lambda: booking_data)
    assert isinstance(result, BookingNotFound)
    assert result.id == "CW-1023"
    assert result.result == "not_found"
    assert result.message == "Booking CW-1023 not found"


def test_empty_source():
    result = get_booking("CW-1001", booking_loader=lambda: {})
    assert isinstance(result, BookingNotFound)


def test_injected_sources_are_independent(booking_data):
    assert isinstance(
        get_booking("CW-1001", booking_loader=lambda: booking_data), BookingRead
    )
    assert isinstance(
        get_booking("CW-1001", booking_loader=lambda: {}), BookingNotFound
    )


@pytest.mark.parametrize("status", ["confirmed", "cancelled", "completed", "in_progress"])
def test_supported_statuses(booking_payload, status):
    booking = BookingBase.model_validate({**booking_payload, "status": status})
    assert booking.status.value == status


def test_typed_fields(booking_payload):
    booking = BookingRead.model_validate(booking_payload)
    assert booking.start.utcoffset().total_seconds() == 7200
    assert booking.end > booking.start
    for amount in (booking.rental_price_eur, booking.booking_fee_eur, booking.deposit_eur):
        assert isinstance(amount, Decimal)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "pending"),
        ("bike_type", "motorbike"),
        ("paid_with", "cash"),
        ("bikes", 0),
        ("bikes", -1),
        ("bikes", True),
        ("bikes", 1.5),
        ("start", "2026-06-13T10:00:00"),
        ("end", "2026-06-15T10:00:00"),
        ("end", "2026-06-13T10:00:00+02:00"),
        ("end", "2026-06-12T10:00:00+02:00"),
        ("rental_price_eur", "-0.01"),
        ("booking_fee_eur", "-1"),
        ("deposit_eur", "-1"),
        ("deposit_eur", "NaN"),
        ("deposit_eur", "Infinity"),
    ],
)
def test_invalid_fields(booking_payload, field, value):
    with pytest.raises(ValidationError):
        BookingBase.model_validate({**booking_payload, field: value})


def test_read_model_prevents_field_reassignment(booking_data):
    with pytest.raises(ValidationError):
        booking_data["CW-1001"].status = "cancelled"


def test_loader_reads_separate_files(tmp_path, booking_payload):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(json.dumps([booking_payload]), encoding="utf-8")
    second.write_text("[]", encoding="utf-8")
    assert "CW-1001" in load_booking(first)
    assert load_booking(second) == {}


def test_source_failure_is_not_reported_as_not_found():
    def failing_loader():
        raise OSError("Booking source unavailable")

    with pytest.raises(OSError, match="Booking source unavailable"):
        get_booking("CW-1001", booking_loader=failing_loader)


def test_missing_file(tmp_path):
    """A missing source raises FileNotFoundError, not BookingNotFound."""
    missing_path = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError):
        get_booking("CW-1001", booking_loader=lambda: load_booking(missing_path))


def test_malformed_json(tmp_path):
    """A broken JSON source raises a decoding error."""
    path = tmp_path / "broken.json"
    path.write_text('[{"id":', encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        get_booking("CW-1001", booking_loader=lambda: load_booking(path))


def test_failed_load_does_not_leave_partial_data(tmp_path, booking_payload):
    """After a validation failure, a new load reads the complete corrected source."""
    path = tmp_path / "bookings.json"
    invalid_booking = {**booking_payload, "id": "CW-1002", "status": "invalid"}
    path.write_text(json.dumps([booking_payload, invalid_booking]), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_booking(path)

    corrected_booking = {**booking_payload, "id": "CW-1002"}
    path.write_text(json.dumps([corrected_booking]), encoding="utf-8")
    result = load_booking(path)
    assert set(result) == {"CW-1002"}
    assert result["CW-1002"].model_dump() == BookingRead.model_validate(
        corrected_booking
    ).model_dump()


def test_duplicate_booking_ids(tmp_path, booking_payload):
    """Duplicate IDs should produce a data error rather than silently overwrite."""
    path = tmp_path / "duplicates.json"
    duplicate_booking = {**booking_payload, "rental_price_eur": "99.00"}
    path.write_text(
        json.dumps([booking_payload, duplicate_booking]), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="Duplicate booking ID: CW-1001"):
        load_booking(path)
