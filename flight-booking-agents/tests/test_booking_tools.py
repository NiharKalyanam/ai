"""
tests/test_booking_tools.py — Unit Tests for Booking Agent

HOW TO RUN:
  pytest tests/test_booking_tools.py -v
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.models import BookingRequest, CancelRequest
from agents.booking_agent.tools import book_flight, cancel_booking, get_booking


def test_book_valid_flight():
    """Booking a valid flight should return a booking ID."""
    request = BookingRequest(
        flight_id="AA101",
        passenger_name="Test User",
        email="test@example.com"
    )
    result = book_flight(request)
    assert result["success"] is True
    assert "BK-AA101" in result["booking_id"]
    assert result["price"] > 0


def test_book_invalid_flight():
    """Booking a non-existent flight should fail gracefully."""
    request = BookingRequest(
        flight_id="XX999",
        passenger_name="Test User",
        email="test@example.com"
    )
    result = book_flight(request)
    assert result["success"] is False
    assert "not found" in result["error"]


def test_cancel_booking():
    """Booking then cancelling should both succeed."""
    # First book
    book_result = book_flight(BookingRequest(
        flight_id="DL303",
        passenger_name="Cancel Me",
        email="cancel@test.com"
    ))
    assert book_result["success"] is True

    # Then cancel
    cancel_result = cancel_booking(CancelRequest(booking_id=book_result["booking_id"]))
    assert cancel_result["success"] is True
