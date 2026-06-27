"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
shared/models.py — Shared Data Models
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT IS THIS FILE?
  All 3 agents need to agree on what a "Flight" or "Booking" looks like.
  Instead of defining the same class 3 times in 3 different files,
  we define them ONCE here and import them everywhere.

WHY SHARED MODELS?
  ✓ Single source of truth — change in one place, all agents updated
  ✓ Consistency — Search Agent and Booking Agent use the exact same Flight shape
  ✓ Real-world practice — production systems always have shared contracts

USED BY:
  - search_agent/tools.py    → returns Flight objects
  - booking_agent/tools.py   → creates Booking objects
  - notification_agent/tools.py → creates Notification objects
  - orchestrator/main.py     → reads all of the above
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════
# FLIGHT MODELS
# ══════════════════════════════════════════════

class Flight(BaseModel):
    """
    Represents one flight option returned by the Search Agent.
    This is what search_flights() returns.
    """
    flight_id:        str            # e.g. "AA101"
    airline:          str            # e.g. "American Airlines"
    origin:           str            # e.g. "JFK"
    destination:      str            # e.g. "LAX"
    departure:        str            # ISO datetime string
    arrival:          str            # ISO datetime string
    price:            float          # USD
    seats_available:  int
    seat_class:       str = "Economy"
    duration_minutes: Optional[int] = None


class FlightSearchRequest(BaseModel):
    """Input shape for searching flights."""
    origin:      str = Field(..., description="Departure IATA code e.g. JFK")
    destination: str = Field(..., description="Arrival IATA code e.g. LAX")
    date:        str = Field(..., description="Travel date YYYY-MM-DD")


class FlightSearchResult(BaseModel):
    """Output shape returned by search_flights tool."""
    success:  bool
    count:    int
    flights:  list[Flight]
    source:   str = "mock"   # "mock" or "aviationstack"
    message:  Optional[str] = None


# ══════════════════════════════════════════════
# BOOKING MODELS
# ══════════════════════════════════════════════

class BookingRequest(BaseModel):
    """Input shape for booking a flight."""
    flight_id:      str
    passenger_name: str
    email:          str
    seat_class:     str = "Economy"


class Booking(BaseModel):
    """Represents a confirmed (or cancelled) booking."""
    booking_id:     str
    flight_id:      str
    passenger_name: str
    email:          str
    seat_class:     str
    price:          float
    status:         str   # "confirmed" | "cancelled"
    booked_at:      str
    cancelled_at:   Optional[str] = None
    cancel_reason:  Optional[str] = None


class CancelRequest(BaseModel):
    """Input shape for cancelling a booking."""
    booking_id: str
    reason:     str = "Customer requested cancellation"


# ══════════════════════════════════════════════
# NOTIFICATION MODELS
# ══════════════════════════════════════════════

class WebhookEvent(BaseModel):
    """
    Shape of an incoming webhook event from an external service.
    External systems (Skyscanner, airline APIs) POST this to us.
    """
    event_type:    str              # "price_drop" | "delay" | "cancellation" | "gate_change"
    flight_id:     str
    message:       str
    old_price:     Optional[float] = None
    new_price:     Optional[float] = None
    delay_minutes: Optional[int]   = None
    metadata:      Optional[dict]  = None


class Notification(BaseModel):
    """A stored notification for the user."""
    id:            int
    event_type:    str
    flight_id:     str
    message:       str
    old_price:     Optional[float] = None
    new_price:     Optional[float] = None
    delay_minutes: Optional[int]   = None
    received_at:   str
    read:          bool = False
    simulated:     bool = False
