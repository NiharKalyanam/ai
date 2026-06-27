"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
agents/notification_agent/server.py — Webhook HTTP Server
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT IS THIS FILE?
  FastAPI server that RECEIVES incoming webhook events.
  HTTP routing only — actual logic lives in tools.py.

TRANSPORT: Webhook (event-driven HTTP)
  Unlike normal APIs where YOU call THEM,
  webhooks mean THEY call YOU when something happens.

  External Service (Skyscanner) → detects price drop
  → POST http://your-server:8002/webhook
  → Our server receives it, stores it, notifies user

HOW TO RUN:
  python agents/notification_agent/server.py

HOW TO TEST WITHOUT A REAL EXTERNAL SERVICE:
  POST to /simulate — it pretends to be Skyscanner sending you an event.
  Open: http://localhost:8002/docs for interactive testing.
"""

import json
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware

from shared.models import WebhookEvent
from agents.notification_agent.tools import (
    verify_signature, process_webhook_event,
    get_notifications, mark_as_read, clear_all, track_flight
)
from config.settings import NOTIFICATION_AGENT_PORT

app = FastAPI(
    title="🔔 Notification Agent",
    description="Webhook server — receives flight events and stores notifications.",
    version="1.0.0"
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Health Check ───────────────────────────────
@app.get("/")
async def root():
    stats = get_notifications()
    return {
        "status": "running",
        "agent":  "Notification Agent (Webhook)",
        "total_notifications": stats["total"],
    }


# ── Webhook Receiver ───────────────────────────
@app.post("/webhook")
async def receive_webhook(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None)
    # ↑ FastAPI auto-extracts X-Webhook-Signature header
):
    """
    THE MAIN WEBHOOK ENDPOINT.
    External services POST here when a flight event occurs.

    Security: If X-Webhook-Signature header is present, we verify it.
    If the signature doesn't match → reject with 401.

    Always returns fast (< 1 second) — external services have short timeouts.
    """
    body = await request.body()

    # Verify signature if provided
    if x_webhook_signature:
        if not verify_signature(body, x_webhook_signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse event
    try:
        event = WebhookEvent(**json.loads(body))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")

    return process_webhook_event(event, simulated=False)

 
# ── Notification Endpoints ─────────────────────
@app.get("/notifications")
async def api_get_notifications(unread_only: bool = False):
    """
    Get all notifications.
    Test: curl http://localhost:8002/notifications
    Test: curl "http://localhost:8002/notifications?unread_only=true"
    """
    return get_notifications(unread_only)


@app.post("/notifications/{notification_id}/read")
async def api_mark_read(notification_id: int):
    """Mark a notification as read."""
    result = mark_as_read(notification_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.delete("/notifications")
async def api_clear():
    """Clear all notifications. Useful for testing."""
    return clear_all()


# ── Simulate Endpoint (Learning Tool) ─────────
@app.post("/simulate")
async def api_simulate(event: WebhookEvent):
    """
    LEARNING TOOL: Simulate an incoming webhook event.

    Use this to test webhook handling without a real external service.
    Pretends to be Skyscanner/airline sending you an event.

    Test a price drop:
    curl -X POST http://localhost:8002/simulate
         -H "Content-Type: application/json"
         -d '{"event_type":"price_drop","flight_id":"AA101",
              "old_price":299.99,"new_price":199.99,
              "message":"Price dropped $100!"}'

    Test a delay:
    curl -X POST http://localhost:8002/simulate
         -H "Content-Type: application/json"
         -d '{"event_type":"delay","flight_id":"UA202",
              "delay_minutes":45,"message":"45 min delay"}'
    """
    result = process_webhook_event(event, simulated=True)
    result["tip"] = "Check GET /notifications to see it!"
    return result


# ── MCP Protocol Endpoint ──────────────────────
@app.post("/mcp")
async def mcp_handler(request: dict):
    """MCP endpoint for Orchestrator integration."""
    tool = request.get("tool")
    args = request.get("arguments", {})

    if tool == "get_notifications":
        return get_notifications(unread_only=args.get("unread_only", False))
    elif tool == "track_flight":
        return track_flight(args.get("flight_id", ""))
    else:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {tool}")


if __name__ == "__main__":
    print(f"🚀 Notification Agent (Webhook) starting on port {NOTIFICATION_AGENT_PORT}")
    print(f"📖 Swagger UI:    http://localhost:{NOTIFICATION_AGENT_PORT}/docs")
    print(f"🔔 Notifications: http://localhost:{NOTIFICATION_AGENT_PORT}/notifications")
    print(f"🧪 Simulate:      http://localhost:{NOTIFICATION_AGENT_PORT}/simulate")
    uvicorn.run("server:app", host="0.0.0.0", port=NOTIFICATION_AGENT_PORT, reload=True)
