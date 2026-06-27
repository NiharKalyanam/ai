"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
tests/test_search_tools.py — Unit Tests for Search Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT IS THIS FILE?
  Unit tests for the Search Agent's tools.py.
  We test the LOGIC directly, without starting any MCP server.
  This is why separating tools.py from server.py is so valuable.

HOW TO RUN:
  pip install pytest
  pytest tests/

WHY WRITE TESTS?
  ✓ Catch bugs before they reach the running system
  ✓ When you add real API later, tests verify mock still works
  ✓ Documents expected behavior as runnable code
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.search_agent.tools import search_flights, get_flight_price


def test_search_flights_found():
    """Searching JFK→LAX should return results from mock data."""
    result = search_flights("JFK", "LAX", "2025-02-01")
    assert result.success is True
    assert result.count > 0
    assert result.flights[0].origin == "JFK"
    assert result.flights[0].destination == "LAX"


def test_search_flights_not_found():
    """Searching a route with no mock data should return 0 results."""
    result = search_flights("ZZZ", "YYY", "2025-02-01")
    assert result.success is True
    assert result.count == 0


def test_get_flight_price_found():
    """Getting price for a real flight ID should return price details."""
    result = get_flight_price("AA101")
    assert result["found"] is True
    assert result["price"] > 0


def test_get_flight_price_not_found():
    """Getting price for unknown flight ID should say not found."""
    result = get_flight_price("XX999")
    assert result["found"] is False
