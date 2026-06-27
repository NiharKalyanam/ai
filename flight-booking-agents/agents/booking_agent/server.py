import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from shared.models import BookingRequest, CancelRequest
from agents.booking_agent.tools import book_flight, cancel_booking, list_bookings, get_booking
from config.settings import BOOKING_AGENT_PORT

app = FastAPI(
    title="✈️ Booking Agent",
    description="HTTP MCP Server — books and cancels flights. See /docs for interactive testing.",
    version="1.0.0"
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# Health Check
@app.get("/")
async def root():
    """Health check. Test: curl http://localhost:8001/"""
    return {"status": "running", "agent": "Booking Agent", "port": BOOKING_AGENT_PORT}


# Booking Endpoints
@app.post("/book")
async def api_book_flight(request: BookingRequest):
    """
    Book a flight.
    Test: curl -X POST http://localhost:8001/book -H "Content-Type: application/json"
          -d '{"flight_id":"AA101","passenger_name":"Alice","email":"alice@test.com"}'
    """
    result = book_flight(request)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/cancel")
async def api_cancel_booking(request: CancelRequest):
    """
    Cancel a booking.
    Test: curl -X POST http://localhost:8001/cancel -H "Content-Type: application/json"
          -d '{"booking_id":"BK-AA101-XXXXX"}'
    """
    result = cancel_booking(request)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/bookings")
async def api_list_bookings():
    """List all bookings. Test: curl http://localhost:8001/bookings"""
    return list_bookings()


@app.get("/bookings/{booking_id}")
async def api_get_booking(booking_id: str):
    """Get one booking. Test: curl http://localhost:8001/bookings/BK-AA101-XXXXX"""
    result = get_booking(booking_id)
    if not result["found"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# MCP Protocol Endpoint
@app.post("/mcp")
async def mcp_handler(request: dict):
    """
    MCP-style endpoint used by the Orchestrator.
    Accepts: {"tool": "book_flight", "arguments": {...}}
    """
    tool = request.get("tool")
    args = request.get("arguments", {})

    if tool == "book_flight":
        return book_flight(BookingRequest(**args))
    elif tool == "cancel_booking":
        return cancel_booking(CancelRequest(**args))
    elif tool == "list_bookings":
        return list_bookings()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {tool}")


if __name__ == "__main__":
    print(f"🚀 Booking Agent starting on port {BOOKING_AGENT_PORT}")
    print(f"📖 Swagger UI: http://localhost:{BOOKING_AGENT_PORT}/docs")
    uvicorn.run("server:app", host="0.0.0.0", port=BOOKING_AGENT_PORT, reload=True)
