"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
agents/notification_agent/tools.py — Notification Logic
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT IS THIS FILE?
  Business logic for the Notification Agent.
  Handles storing, retrieving, and marking notifications.

  server.py handles webhook HTTP routing.
  THIS file decides what to DO with received webhook events.

WEBHOOK FLOW:
  External Service → POST /webhook → server.py receives it
  → calls process_webhook_event() in THIS file
  → stores notification → ready for user to read
"""

import hashlib
import hmac
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.models import WebhookEvent, Notification
from config.settings import WEBHOOK_SECRET

# In-memory notification store
# In production: replace with Redis, PostgreSQL, etc.
_notifications: list[dict] = []


# ══════════════════════════════════════════════
# WEBHOOK PROCESSING
# ══════════════════════════════════════════════

def verify_signature(body: bytes, signature: str) -> bool:
    """
    Verify a webhook request is genuinely from the expected sender.

    HOW IT WORKS:
      You and the external service share a secret key.
      They HMAC-sign the request body with it and put the result in a header.
      You compute the same signature and compare.
      If they match → legitimate. If not → reject (could be an attacker).

    WHY THIS MATTERS:
      Without signature verification, ANYONE could POST fake events to your webhook.
      Imagine someone sending "price_drop: $0" to trick you into thinking it's a deal.
    """
    expected = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def process_webhook_event(event: WebhookEvent, simulated: bool = False) -> dict:
    """
    Store an incoming webhook event as a notification.

    Args:
        event:     The parsed WebhookEvent
        simulated: True if this came from /simulate (not a real external service)

    Returns:
        Dict with notification ID and confirmation message
    """
    notification = {
        "id":            len(_notifications) + 1,
        "event_type":    event.event_type,
        "flight_id":     event.flight_id,
        "message":       event.message,
        "old_price":     event.old_price,
        "new_price":     event.new_price,
        "delay_minutes": event.delay_minutes,
        "metadata":      event.metadata,
        "received_at":   datetime.now().isoformat(),
        "read":          False,
        "simulated":     simulated,
    }
    _notifications.append(notification)

    emoji_map = {
        "price_drop":     "💸",
        "price_increase": "📈",
        "delay":          "⏰",
        "cancellation":   "❌",
        "gate_change":    "🚪",
    }
    emoji = emoji_map.get(event.event_type, "🔔")
    print(f"\n{emoji} {'[SIMULATED] ' if simulated else ''}WEBHOOK: {event.event_type} — {event.message}")

    return {
        "received":        True,
        "notification_id": notification["id"],
        "message":         "Webhook processed",
    }


# ══════════════════════════════════════════════
# NOTIFICATION RETRIEVAL
# ══════════════════════════════════════════════

def get_notifications(unread_only: bool = False) -> dict:
    """Return stored notifications, optionally filtered to unread only."""
    result = [n for n in _notifications if not n["read"]] if unread_only else list(_notifications)
    return {"total": len(result), "notifications": result}


def mark_as_read(notification_id: int) -> dict:
    """Mark a notification as read."""
    notif = next((n for n in _notifications if n["id"] == notification_id), None)
    if not notif:
        return {"success": False, "error": f"Notification {notification_id} not found"}
    notif["read"] = True
    return {"success": True, "message": f"Notification {notification_id} marked as read"}


def clear_all() -> dict:
    """Clear all notifications (useful for testing)."""
    count = len(_notifications)
    _notifications.clear()
    return {"cleared": count}


def track_flight(flight_id: str) -> dict:
    """
    Register interest in tracking a flight for price/delay changes.

    In production:
      This would tell an external service (Skyscanner API, airline API)
      to send webhooks to our /webhook endpoint when something changes.

    For now:
      We just return the webhook URL they should POST to.
    """
    return {
        "success":     True,
        "flight_id":   flight_id,
        "message":     f"Now tracking {flight_id}",
        "webhook_url": "http://localhost:8002/webhook",
        "tip":         f"Use POST /simulate to test events for {flight_id}",
    }
