"""Booking models, JSON loading, and lookup with explicit dependencies."""

from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class BookingStatus(StrEnum):
    """Statuses supported by the supplied booking data."""
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"

Money = Annotated[Decimal, Field(ge=0, allow_inf_nan=False)]


class BookingBase(BaseModel):
    """Shared validated booking fields."""

    id: str
    status: BookingStatus
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
