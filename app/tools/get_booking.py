"""Booking models, JSON loading, and lookup with explicit dependencies."""

from collections.abc import Callable, Mapping
from decimal import Decimal
from enum import StrEnum
import json
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class BookStatus(StrEnum):
    """Statuses supported by the supplied booking data."""

    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"


Money = Annotated[Decimal, Field(ge=0, allow_inf_nan=False)]


class BookingBase(BaseModel):
    """Shared validated booking fields."""

    id: str
    status: BookStatus
    bike_type: Literal["city", "e-bike", "kids"]
    bikes: Annotated[int, Field(gt=0, strict=True)]
    start: AwareDatetime
    end: AwareDatetime
    add_ons: list[str]
    rental_price_eur: Money
    booking_fee_eur: Money
    deposit_eur: Money
    paid_with: Literal["card", "voucher"]

    @model_validator(mode="after")
    def validate_rental_period(self) -> Self:
        if self.end <= self.start:
            raise ValueError("Rental end must be after its start")
        return self


class BookingRead(BookingBase):
    """Read model preventing field reassignment; nested lists remain mutable."""

    model_config = ConfigDict(frozen=True)


class BookingNotFound(BaseModel):
    """Lookup result when no booking matches the id."""

    id: str
    result: Literal["not_found"] = "not_found"
    message: str


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


def get_booking(
    booking_id: str, *, booking_loader: BookingLoader = load_booking
) -> BookingRead | BookingNotFound:
    """Look up an exact ID with an injected loader, defaulting to the JSON file.

    The agent adapter will supply dependencies in Python; the model only needs
    to provide booking_id.
    """
    bookings = booking_loader()
    booking = bookings.get(booking_id)
    if booking is None:
        return BookingNotFound(
            id=booking_id,
            message=f"Booking {booking_id} not found",
        )
    return booking
