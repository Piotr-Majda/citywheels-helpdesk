"""Booking models, JSON loading, and lookup with explicit dependencies."""

from collections.abc import Callable, Mapping
from decimal import Decimal
import json
from pathlib import Path

from app.models.booking import BookingRead


BOOKINGS_PATH = Path(__file__).resolve().parents[2] / "data" / "bookings.json"


def load_booking(path: Path = BOOKINGS_PATH) -> dict[str, BookingRead]:
    """Load a fresh validated index; loading errors propagate to the caller."""
    with path.open(encoding="utf-8") as file:
        data = json.load(file, parse_float=Decimal)

    bookings = {}
    for booking_data in data:
        booking = BookingRead.model_validate(booking_data)
        if booking.id in bookings:
            raise ValueError(f"Duplicate booking ID: {booking.id}")
        bookings[booking.id] = booking
    return bookings


BookingLoader = Callable[[], Mapping[str, BookingRead]]
