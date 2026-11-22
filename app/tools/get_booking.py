"""Booking models, JSON loading, and lookup with explicit dependencies."""
from app.db.booking_loader import BookingLoader, load_booking
from app.models.booking import BookingNotFound, BookingRead


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
