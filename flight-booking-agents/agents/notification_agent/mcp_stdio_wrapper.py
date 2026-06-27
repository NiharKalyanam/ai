"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
agents/notification_agent/mcp_stdio_wrapper.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT IS THIS FILE?
  A STDIO wrapper for the Notification Agent.

WHY DO WE NEED THIS?
  Claude Desktop only speaks STDIO.
  Our notification agent is a FastAPI HTTP server (port 8002).
  
  This wrapper sits in between:
    Claude Desktop (STDIO) → this file → HTTP → localhost:8002
  
  Claude Desktop launches THIS file via STDIO.
  THIS file forwards requests to the HTTP server.
  Responses come back the same way in reverse.

SO THE FLOW IS:
  Claude Desktop --> STDIO
  mcp_stdio_wrapper.py --> HTTP  <-- Claude Desktop launches this
  notification_agent/server.py (FastAPI on port 8002) <-- you run this manually
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import requests
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

NOTIFICATION_URL = "http://localhost:8002"

server = Server("flight-notification-agent")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_flight_notifications",
            description=(
                "Get flight price drop and delay alerts from the flight booking system. "
                "Use this to check if any tracked flights have changed in price or been delayed. "
                "Do NOT use Gmail or email for this — this is a dedicated flight alert system."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "unread_only": {
                        "type": "boolean",
                        "description": "If true, return only unread notifications. Default false."
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="track_flight",
            description="Start tracking a flight for price changes and delays.",
            inputSchema={
                "type": "object",
                "properties": {
                    "flight_id": {
                        "type": "string",
                        "description": "Flight ID to track e.g. DL303"
                    }
                },
                "required": ["flight_id"]
            }
        ),
        types.Tool(
            name="simulate_flight_event",
            description="Simulate a flight event like a price drop or delay for testing.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_type":    {"type": "string", "description": "price_drop, delay, or cancellation"},
                    "flight_id":     {"type": "string", "description": "Flight ID e.g. DL303"},
                    "message":       {"type": "string", "description": "Description of the event"},
                    "old_price":     {"type": "number", "description": "Previous price (for price events)"},
                    "new_price":     {"type": "number", "description": "New price (for price events)"},
                    "delay_minutes": {"type": "integer", "description": "Delay in minutes (for delay events)"}
                },
                "required": ["event_type", "flight_id", "message"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:

    # Check if HTTP server is running
    try:
        requests.get(f"{NOTIFICATION_URL}/", timeout=3)
    except requests.exceptions.ConnectionError:
        return [types.TextContent(type="text", text=(
            " Notification Agent is not running!\n"
            "Please start it first:\n"
            "  python3 agents/notification_agent/server.py"
        ))]

    #  get_flight_notifications
    if name == "get_flight_notifications":
        unread_only = arguments.get("unread_only", False)
        response = requests.get(
            f"{NOTIFICATION_URL}/notifications",
            params={"unread_only": unread_only},
            timeout=10
        )
        data = response.json()
        notifications = data.get("notifications", [])

        if not notifications:
            text = "📭 No flight notifications yet.\nTip: Ask me to simulate a price drop to test it!"
        else:
            emoji_map = {
                "price_drop":     "💸",
                "price_increase": "📈",
                "delay":          "⏰",
                "cancellation":   "❌",
                "gate_change":    "🚪",
            }
            lines = [f"🔔 You have {len(notifications)} flight notification(s):\n"]
            for n in notifications:
                emoji = emoji_map.get(n["event_type"], "🔔")
                lines.append(f"{emoji} [{n['event_type'].upper()}] Flight {n['flight_id']}")
                lines.append(f"   {n['message']}")
                if n.get("old_price") and n.get("new_price"):
                    saving = n["old_price"] - n["new_price"]
                    lines.append(f"   Was ${n['old_price']} → Now ${n['new_price']} (save ${saving:.2f}!)")
                if n.get("delay_minutes"):
                    lines.append(f"   Delayed by {n['delay_minutes']} minutes")
                lines.append(f"   Received: {n['received_at']}\n")
            text = "\n".join(lines)

    #  track_flight 
    elif name == "track_flight":
        response = requests.post(
            f"{NOTIFICATION_URL}/mcp",
            json={"tool": "track_flight", "arguments": arguments},
            timeout=10
        )
        data = response.json()
        text = f" Now tracking flight {arguments.get('flight_id')}\nWebhook URL: {data.get('webhook_url', 'http://localhost:8002/webhook')}"

    #  simulate_flight_event 
    elif name == "simulate_flight_event":
        response = requests.post(
            f"{NOTIFICATION_URL}/simulate",
            json=arguments,
            timeout=10
        )
        data = response.json()
        text = f" Simulated event created!\n{data.get('message', '')}\nCheck your notifications now."

    else:
        text = f"Unknown tool: {name}"

    return [types.TextContent(type="text", text=text)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())