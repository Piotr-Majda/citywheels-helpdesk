"""Shared payload fixtures; unit tests inject their own booking source."""

import json
from pathlib import Path

import pytest

from app.models.booking import BookingRead


@pytest.fixture
def booking_payloads():
    fixture_path = Path(__file__).with_name("fake_booking.json")
    return json.loads(fixture_path.read_text(encoding="utf-8"))


@pytest.fixture
def booking_payload(booking_payloads):
    return booking_payloads[0].copy()


@pytest.fixture
def booking_data(booking_payloads):
    bookings = [BookingRead.model_validate(payload) for payload in booking_payloads]
    return {booking.id: booking for booking in bookings}
