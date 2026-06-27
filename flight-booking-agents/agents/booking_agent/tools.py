import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.models import BookingRequest, CancelRequest
from config.settings import USE_DB

# Pick the right adapter based on config
if USE_DB == "postgres":
    from agents.booking_agent.adapters import postgres_adapter as adapter
else:
    from agents.booking_agent.adapters import json_adapter as adapter


# ══════════════════════════════════════════════
# TOOL FUNCTIONS — called by server.py
# ══════════════════════════════════════════════

def book_flight(request: BookingRequest) -> dict:
    """Book a flight. Delegates to active storage adapter."""
    return adapter.create_booking(
        flight_id=      request.flight_id,
        passenger_name= request.passenger_name,
        email=          request.email,
        seat_class=     request.seat_class,
    )


def cancel_booking(request: CancelRequest) -> dict:
    """Cancel a booking. Delegates to active storage adapter."""
    return adapter.cancel_booking(request.booking_id, request.reason)


def get_booking(booking_id: str) -> dict:
    """Get one booking. Delegates to active storage adapter."""
    return adapter.get_booking(booking_id)


def list_bookings() -> dict:
    """Get all bookings. Delegates to active storage adapter."""
    return adapter.get_all()
