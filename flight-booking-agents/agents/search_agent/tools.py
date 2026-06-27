import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.models import FlightSearchResult
from config.settings import USE_REAL_API

# Import both adapters
from agents.search_agent.adapters import mock_adapter, aviationstack_adapter

# which adapter to use. Change USE_REAL_API in .env → everything switches.
adapter = aviationstack_adapter if USE_REAL_API else mock_adapter


def search_flights(origin: str, destination: str, date: str) -> FlightSearchResult:
    """
    Search for available flights.
    Delegates to whichever adapter is active (mock or real API).

    tools.py doesn't know or care which adapter runs.
    It just calls search() and gets back FlightSearchResult.
    """
    return adapter.search(origin, destination, date)


def get_flight_price(flight_id: str) -> dict:
    """
    Get price details for a specific flight.
    Delegates to the active adapter.
    """
    return adapter.get_price(flight_id)
