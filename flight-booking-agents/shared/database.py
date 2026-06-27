"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
shared/database.py — Shared Data Access Layer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT IS THIS FILE?
  All agents need to read/write flights.json.
  Instead of each agent opening files differently,
  this file handles ALL database operations in one place.

WHY A SHARED DATABASE MODULE?
  ✓ If you switch from JSON to PostgreSQL later, you only change THIS file
  ✓ No duplicated file-reading code across agents
  ✓ Consistent error handling everywhere

IN PRODUCTION:
  This would be replaced by a real database client:
  - SQLAlchemy (PostgreSQL/MySQL)
  - Motor (MongoDB async)
  - Redis client (for caching)
"""

import json
from pathlib import Path
from typing import Optional

# Path to our JSON "database" file
DB_PATH = Path(__file__).parent.parent / "mock_data" / "flights.json"


def _load() -> dict:
    """Load full database from JSON file."""
    with open(DB_PATH, "r") as f:
        return json.load(f)


def _save(data: dict):
    """Save full database back to JSON file."""
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=2)


# ── Flights ────────────────────────────────────
def get_all_flights() -> list[dict]:
    return _load()["flights"]


def get_flight_by_id(flight_id: str) -> Optional[dict]:
    return next((f for f in get_all_flights() if f["flight_id"] == flight_id), None)


def decrement_seat(flight_id: str):
    """Reduce available seat count by 1 when a booking is made."""
    data = _load()
    for f in data["flights"]:
        if f["flight_id"] == flight_id:
            f["seats_available"] = max(0, f["seats_available"] - 1)
            break
    _save(data)


def increment_seat(flight_id: str):
    """Restore a seat when a booking is cancelled."""
    data = _load()
    for f in data["flights"]:
        if f["flight_id"] == flight_id:
            f["seats_available"] += 1
            break
    _save(data)


# ── Bookings ───────────────────────────────────
def get_all_bookings() -> list[dict]:
    return _load()["bookings"]


def get_booking_by_id(booking_id: str) -> Optional[dict]:
    return next((b for b in get_all_bookings() if b["booking_id"] == booking_id), None)


def save_booking(booking: dict):
    """Add a new booking to the database."""
    data = _load()
    data["bookings"].append(booking)
    _save(data)


def update_booking(booking_id: str, updates: dict):
    """Update fields on an existing booking."""
    data = _load()
    for b in data["bookings"]:
        if b["booking_id"] == booking_id:
            b.update(updates)
            break
    _save(data)
