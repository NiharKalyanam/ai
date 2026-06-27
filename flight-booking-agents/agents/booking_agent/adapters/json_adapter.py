"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
agents/booking_agent/adapters/json_adapter.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT IS THIS FILE?
  The JSON Adapter for the Booking Agent.
  Saves and reads bookings from flights.json file.
  Used in development/learning (no real database needed).

"""

import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.database import (
    get_flight_by_id, get_booking_by_id,
    save_booking, update_booking,
    decrement_seat, increment_seat,
    get_all_bookings
)


def create_booking(flight_id: str, passenger_name: str, email: str, seat_class: str) -> dict:
    """
    Create a new booking and save to flights.json.

    Returns:
        Dict with booking confirmation or error
    """
    # Validate flight exists
    flight = get_flight_by_id(flight_id)
    if not flight:
        return {"success": False, "error": f"Flight {flight_id} not found"}

    # Check seats
    if flight["seats_available"] <= 0:
        return {"success": False, "error": f"No seats available on {flight_id}"}

    # Create booking record
    booking_id = f"BK-{flight_id}-{str(uuid.uuid4())[:6].upper()}"
    booking = {
        "booking_id":     booking_id,
        "flight_id":      flight_id,
        "passenger_name": passenger_name,
        "email":          email,
        "seat_class":     seat_class,
        "price":          flight["price"],
        "status":         "confirmed",
        "booked_at":      datetime.now().isoformat(),
        "storage":        "json",          # tracks which adapter saved this
    }

    save_booking(booking)
    decrement_seat(flight_id)

    return {
        "success":    True,
        "booking_id": booking_id,
        "flight_id":  flight_id,
        "passenger":  passenger_name,
        "price":      flight["price"],
        "status":     "confirmed",
        "message":    f"✅ Booking confirmed! ID: {booking_id}",
        "booked_at":  booking["booked_at"],
    }


def cancel_booking(booking_id: str, reason: str) -> dict:
    """Cancel a booking in flights.json."""
    booking = get_booking_by_id(booking_id)
    if not booking:
        return {"success": False, "error": f"Booking {booking_id} not found"}

    if booking["status"] == "cancelled":
        return {"success": False, "error": "Already cancelled"}

    update_booking(booking_id, {
        "status":        "cancelled",
        "cancelled_at":  datetime.now().isoformat(),
        "cancel_reason": reason,
    })
    increment_seat(booking["flight_id"])

    return {
        "success":    True,
        "booking_id": booking_id,
        "message":    f"Booking {booking_id} cancelled",
        "refund":     f"Refund of ${booking['price']:.2f} in 5-7 business days",
    }


def get_booking(booking_id: str) -> dict:
    """Get a single booking by ID."""
    booking = get_booking_by_id(booking_id)
    if not booking:
        return {"found": False, "error": f"Booking {booking_id} not found"}
    return {"found": True, **booking}


def get_all() -> dict:
    """Get all bookings."""
    bookings = get_all_bookings()
    return {"total": len(bookings), "bookings": bookings}
