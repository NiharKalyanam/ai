import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import requests
from shared.models import Flight, FlightSearchResult
from config.settings import AVIATIONSTACK_API_KEY, AVIATIONSTACK_BASE_URL


def search(origin: str, destination: str, date: str) -> FlightSearchResult:
    """
    Search flights from AviationStack real API.

    Args:
        origin:      IATA code e.g. "JFK"
        destination: IATA code e.g. "LAX"
        date:        "YYYY-MM-DD"

    Returns:
        FlightSearchResult — same shape as mock_adapter.search()

    NOTE:
        AviationStack free tier shows live flights only (not future schedules).
        Price and seat data not available on free tier.
        For full data, a paid plan is needed.
    """
    try:
        response = requests.get(
            f"{AVIATIONSTACK_BASE_URL}/flights",
            params={
                "access_key":  AVIATIONSTACK_API_KEY,
                "dep_iata":    origin,
                "arr_iata":    destination,
                # "flight_date": date,
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        # Normalize AviationStack response into our Flight model
        # Their format is nested — we flatten it
        flights = []
        for item in data.get("data", []):
            flights.append(Flight(
                flight_id=       item.get("flight", {}).get("iata", "UNKNOWN"),
                airline=         item.get("airline", {}).get("name", "Unknown Airline"),
                origin=          item.get("departure", {}).get("iata", origin),
                destination=     item.get("arrival", {}).get("iata", destination),
                departure=       item.get("departure", {}).get("scheduled", ""),
                arrival=         item.get("arrival", {}).get("scheduled", ""),
                price=           0.0,   # not available on free tier
                seats_available= 0,     # not available on free tier
                seat_class=      "Economy",
            ))

        return FlightSearchResult(
            success=True,
            count=len(flights),
            flights=flights,
            source="aviationstack",    # tells caller this came from real API
        )

    except requests.exceptions.ConnectionError:
        return FlightSearchResult(
            success=False,
            count=0,
            flights=[],
            source="aviationstack",
            message="Cannot connect to AviationStack API. Check your internet connection."
        )
    except requests.exceptions.HTTPError as e:
        return FlightSearchResult(
            success=False,
            count=0,
            flights=[],
            source="aviationstack",
            message=f"AviationStack API error: {e}. Check your API key."
        )
    except Exception as e:
        return FlightSearchResult(
            success=False,
            count=0,
            flights=[],
            source="aviationstack",
            message=f"Unexpected error: {e}"
        )


def get_price(flight_id: str) -> dict:
    """
    AviationStack free tier does not provide pricing.
    This is a placeholder for when you upgrade to a paid plan.
    """
    return {
        "found":   False,
        "message": "Price lookup not available on AviationStack free tier. Use mock adapter or upgrade plan.",
        "source":  "aviationstack",
    }
