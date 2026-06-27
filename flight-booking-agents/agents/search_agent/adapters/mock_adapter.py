import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.models import Flight, FlightSearchResult
from shared.database import get_all_flights, get_flight_by_id


def search(origin: str, destination: str, date: str) -> FlightSearchResult:
    """
    Search flights from local mock data (flights.json).

    Args:
        origin:      IATA code e.g. "JFK"
        destination: IATA code e.g. "LAX"
        date:        "YYYY-MM-DD" (not used in mock but kept for API parity)

    Returns:
        FlightSearchResult — same shape as aviationstack_adapter.search()
        This is the key — both adapters return IDENTICAL shapes
        so tools.py doesn't need to know which one ran
    """
    all_flights = get_all_flights()

    # Filter by origin and destination
    matched = [
        f for f in all_flights
        if f["from"].upper() == origin.upper()
        and f["to"].upper() == destination.upper()
    ]

    # Convert raw dicts to Flight model objects
    flights = [
        Flight(
            flight_id=f["flight_id"],
            airline=f["airline"],
            origin=f["from"],
            destination=f["to"],
            departure=f["departure"],
            arrival=f["arrival"],
            price=f["price"],
            seats_available=f["seats_available"],
            seat_class=f["class"],
        )
        for f in matched
    ]

    return FlightSearchResult(
        success=True,
        count=len(flights),
        flights=flights,
        source="mock",                        # tells caller where data came from
        message=None if flights else f"No flights found for {origin}→{destination}"
    )


def get_price(flight_id: str) -> dict:
    """
    Get price details for a specific flight from mock data.

    Args:
        flight_id: e.g. "AA101"

    Returns:
        Dict with price details
    """
    flight = get_flight_by_id(flight_id)

    if not flight:
        return {"found": False, "message": f"Flight {flight_id} not found in mock data"}

    return {
        "found":           True,
        "flight_id":       flight["flight_id"],
        "airline":         flight["airline"],
        "route":           f"{flight['from']} → {flight['to']}",
        "seat_class":      flight["class"],
        "price":           flight["price"],
        "seats_remaining": flight["seats_available"],
        "source":          "mock",
    }
