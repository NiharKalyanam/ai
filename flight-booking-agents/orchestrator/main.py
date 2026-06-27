"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ORCHESTRATOR — The Boss Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT IS THIS FILE?
  The Orchestrator is the "boss" that coordinates all three agents.
  Instead of talking to each agent directly, you talk to the Orchestrator
  and it figures out which agent to call, in what order, with what data.

WHAT DOES IT DO?
  It runs complete "workflows" — multi-step processes that involve
  more than one agent. Example:

  book_flight_workflow():
    Step 1 → Call Search Agent (STDIO via subprocess) to find flights
    Step 2 → Pick the best option
    Step 3 → Call Booking Agent (HTTP POST) to confirm booking
    Step 4 → Call Notification Agent (HTTP POST) to start tracking
    Step 5 → Return the full result to the user

WHY IS THIS IMPORTANT?
  This is the core of multi-agent systems!
  
  Without orchestration:
    User → talks to Search Agent
    User → manually takes result
    User → talks to Booking Agent
    User → manually takes booking ID
    User → talks to Notification Agent
    
  With orchestration:
    User → "book me the cheapest flight JFK→LAX tomorrow"
    Orchestrator → does all of the above automatically → "Done! Booking ID: BK-AA101-XYZ"

WHAT TRANSPORTS ARE USED HERE?
  ┌──────────────────┬────────────────┬──────────────────────────────────┐
  │ Agent            │ Transport      │ How we call it                   │
  ├──────────────────┼────────────────┼──────────────────────────────────┤
  │ Search Agent     │ STDIO          │ subprocess (launch + pipe JSON)  │
  │ Booking Agent    │ HTTP           │ requests.post() to localhost:8001│
  │ Notification     │ HTTP/Webhook   │ requests.post() to localhost:8002│
  └──────────────────┴────────────────┴──────────────────────────────────┘

HOW TO RUN:
  python orchestrator/main.py

HOW TO USE:
  The script shows an interactive menu. Choose a workflow and follow prompts.
"""

import json
import subprocess
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── Load environment variables
load_dotenv()

# ── Agent URLs
BOOKING_AGENT_URL      = "http://localhost:8001"
NOTIFICATION_AGENT_URL = "http://localhost:8002"

# Path to Search Agent
SEARCH_AGENT_PATH = Path(__file__).parent.parent / "agents" / "search_agent" / "server.py"


# ══════════════════════════════════════════════════════════════════════════
# TRANSPORT LAYER — How we talk to each agent
# ══════════════════════════════════════════════════════════════════════════

def call_search_agent_stdio(tool: str, arguments: dict) -> str:
    """
    Call the Search Agent via STDIO transport.
    
    HOW STDIO WORKS IN CODE:
      1. We launch the Search Agent as a child process using subprocess
      2. We write a JSON message to its stdin
      3. We read the JSON response from its stdout
      4. The child process runs, responds, and can keep running or exit
    
    This is EXACTLY what Claude Desktop does automatically when you
    configure the agent in claude_desktop_config.json.
    We're just doing it manually here to show you how it works under the hood.
    
    Args:
        tool:      Tool name to call (e.g. "search_flights")
        arguments: Arguments dict (e.g. {"origin": "JFK", "destination": "LAX", "date": "2025-02-01"})
    
    Returns:
        String response from the agent
    """
    # Build the MCP-format request message
    # This is the actual JSON that flows through stdin
    mcp_request = {
        "jsonrpc": "2.0",         # MCP uses JSON-RPC 2.0 protocol
        "id": 1,                  # Request ID (used to match request/response)
        "method": "tools/call",  # MCP method for calling a tool
        "params": {
            "name": tool,
            "arguments": arguments
        }
    }
    
    print(f"\n [STDIO] Calling Search Agent: {tool}")
    print(f"   Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        result = subprocess.run(
            [sys.executable, str(SEARCH_AGENT_PATH)],
            
            input=json.dumps(mcp_request),  # Send request via stdin
            capture_output=True,             # Capture stdout AND stderr
            text=True,                       # Decode bytes as UTF-8 text
            timeout=30                       # Give it 30 seconds to respond
        )
        
        if result.returncode != 0:
            return f"Search Agent error: {result.stderr}"
        
        # Parse the JSON-RPC response
        response = json.loads(result.stdout)
        
        # Extract the tool result from MCP response format
        # MCP returns: {"result": {"content": [{"type": "text", "text": "..."}]}}
        content = response.get("result", {}).get("content", [])
        if content and content[0].get("type") == "text":
            return content[0]["text"]
        
        return str(response)
        
    except subprocess.TimeoutExpired:
        return "Search Agent timed out"
    except Exception as e:
        return f"Error calling Search Agent: {e}"


def call_booking_agent_http(endpoint: str, payload: dict) -> dict:
    """
    Call the Booking Agent via HTTP transport.
    
    HOW HTTP WORKS IN CODE:
      requests.post() sends an HTTP POST request to the Booking Agent's server.
      The server processes it and returns a JSON response.
    
    This is simple and familiar — just like calling any REST API.
    
    Args:
        endpoint: API path (e.g. "/book", "/cancel", "/bookings")
        payload:  Request body as a dict (will be JSON-encoded)
    
    Returns:
        Response dict from the server
    """
    url = f"{BOOKING_AGENT_URL}{endpoint}"
    
    print(f"\n [HTTP] Calling Booking Agent: POST {url}")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            url,
            json=payload,    # Automatically sets Content-Type: application/json
            timeout=10       # Wait up to 10 seconds
        )
        response.raise_for_status()  # Raise exception for 4xx/5xx errors
        return response.json()
        
    except requests.exceptions.ConnectionError:
        print(f"\n ERROR: Cannot connect to Booking Agent at {BOOKING_AGENT_URL}")
        print("   Make sure the Booking Agent is running: python agents/booking_agent/server.py")
        return {"error": "Booking Agent not running"}
    except Exception as e:
        return {"error": str(e)}


def call_notification_agent_http(endpoint: str, payload: dict = None, method: str = "POST") -> dict:
    """
    Call the Notification Agent via HTTP transport.
    
    Same pattern as booking agent — HTTP is HTTP regardless of which
    agent you're talking to.
    
    Args:
        endpoint: API path (e.g. "/simulate", "/notifications")
        payload:  Request body (optional for GET requests)
        method:   HTTP method ("GET" or "POST")
    
    Returns:
        Response dict
    """
    url = f"{NOTIFICATION_AGENT_URL}{endpoint}"
    
    print(f"\n🔔 [HTTP] Calling Notification Agent: {method} {url}")
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        else:
            print(f"   Payload: {json.dumps(payload or {}, indent=2)}")
            response = requests.post(url, json=payload, timeout=10)
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.ConnectionError:
        print(f"\n ERROR: Cannot connect to Notification Agent at {NOTIFICATION_AGENT_URL}")
        print("   Make sure it's running: python agents/notification_agent/server.py")
        return {"error": "Notification Agent not running"}
    except Exception as e:
        return {"error": str(e)}


# ══════════════════════════════════════════════════════════════════════════
# WORKFLOWS — Multi-step processes that coordinate multiple agents
# ══════════════════════════════════════════════════════════════════════════

def workflow_search_and_book(origin: str, destination: str, date: str,
                              passenger_name: str, email: str):
    """
    WORKFLOW 1: Search → Select → Book → Track
    
    This is the main workflow. It:
      1. Searches for flights (STDIO → Search Agent)
      2. Shows options to the user
      3. Books the selected flight (HTTP → Booking Agent)
      4. Starts tracking the flight (HTTP → Notification Agent)
    """
    print("\n" + "="*60)
    print("✈️  WORKFLOW: Search and Book Flight")
    print("="*60)
    
    # ── STEP 1: Search for flights via STDIO ──────────────────────────────
    print("\n📍 STEP 1: Searching for flights...")
    search_result = call_search_agent_stdio(
        tool="search_flights",
        arguments={
            "origin":      origin,
            "destination": destination,
            "date":        date
        }
    )
    print(f"\n Search Results:\n{search_result}")
    
    # ── STEP 2: User picks a flight ───────────────────────────────────────
    print("\n📍 STEP 2: Which flight would you like to book?")
    flight_id = input("   Enter flight ID (e.g. AA101): ").strip().upper()
    
    if not flight_id:
        print(" No flight selected. Aborting.")
        return
    
    # ── STEP 3: Book the flight via HTTP ──────────────────────────────────
    print(f"\n STEP 3: Booking flight {flight_id}...")
    booking_result = call_booking_agent_http(
        endpoint="/book",
        payload={
            "flight_id":      flight_id,
            "passenger_name": passenger_name,
            "email":          email,
        }
    )
    
    if "error" in booking_result:
        print(f" Booking failed: {booking_result['error']}")
        return
    
    print(f"\n Booking Result:")
    print(f"   {booking_result.get('message', 'Booking created')}")
    print(f"   Booking ID: {booking_result.get('booking_id')}")
    print(f"   Total Price: ${booking_result.get('total_price')}")
    
    booking_id = booking_result.get("booking_id")
    
    # ── STEP 4: Register for flight notifications via Webhook Agent ───────
    print(f"\n STEP 4: Setting up notifications for flight {flight_id}...")
    track_result = call_notification_agent_http(
        endpoint="/mcp",
        payload={
            "tool":      "track_flight",
            "arguments": {"flight_id": flight_id}
        }
    )
    
    if "error" not in track_result:
        print(f"   Now tracking {flight_id} for price changes and delays")
        print(f"   Webhook URL: {track_result.get('webhook_url', 'http://localhost:8002/webhook')}")
    
    # ── DONE ──────────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("🎉 WORKFLOW COMPLETE!")
    print(f"   Passenger:  {passenger_name}")
    print(f"   Flight:     {flight_id}")
    print(f"   Booking ID: {booking_id}")
    print(f"   Tracking:   Active (you'll get notified of changes)")
    print("="*60)


def workflow_check_notifications():
    """
    WORKFLOW 2: Check all unread flight notifications.
    Calls the Notification Agent via HTTP GET.
    """
    print("\n" + "="*60)
    print("🔔 WORKFLOW: Check Notifications")
    print("="*60)
    
    result = call_notification_agent_http(
        endpoint="/notifications?unread_only=true",
        method="GET"
    )
    
    if "error" in result:
        print(f" Error: {result['error']}")
        return
    
    notifications = result.get("notifications", [])
    total         = result.get("total", 0)
    
    if total == 0:
        print("\n📭 No unread notifications.")
        print("   TIP: Use /simulate on the Notification Agent to create test events")
    else:
        print(f"\n📬 You have {total} unread notification(s):\n")
        for n in notifications:
            emoji = {"price_drop": "💸", "delay": "⏰", "cancellation": "❌"}.get(n["event_type"], "🔔")
            print(f"  {emoji} [{n['event_type'].upper()}] Flight {n['flight_id']}")
            print(f"     {n['message']}")
            if n.get("old_price") and n.get("new_price"):
                savings = n["old_price"] - n["new_price"]
                print(f"     Price: ${n['old_price']} → ${n['new_price']} (save ${savings:.2f}!)")
            if n.get("delay_minutes"):
                print(f"     Delay: {n['delay_minutes']} minutes")
            print(f"     Received: {n['received_at']}\n")


def workflow_simulate_event():
    """
    WORKFLOW 3: Simulate an incoming webhook event (for testing).
    This helps you learn how webhooks work without a real external service.
    """
    print("\n" + "="*60)
    print(" WORKFLOW: Simulate Webhook Event")
    print("="*60)
    
    print("\nWhat type of event to simulate?")
    print("  1. Price Drop")
    print("  2. Flight Delay")
    print("  3. Flight Cancellation")
    
    choice = input("\nEnter choice (1-3): ").strip()
    flight_id = input("Enter flight ID (e.g. AA101): ").strip().upper() or "AA101"
    
    if choice == "1":
        payload = {
            "event_type": "price_drop",
            "flight_id":  flight_id,
            "old_price":  299.99,
            "new_price":  199.99,
            "message":    f" Price dropped on {flight_id}! Was $299.99, now $199.99. Save $100!"
        }
    elif choice == "2":
        delay = input("Delay in minutes (default 45): ").strip() or "45"
        payload = {
            "event_type":    "delay",
            "flight_id":     flight_id,
            "delay_minutes": int(delay),
            "message":       f" Flight {flight_id} is delayed by {delay} minutes."
        }
    elif choice == "3":
        payload = {
            "event_type": "cancellation",
            "flight_id":  flight_id,
            "message":    f" Flight {flight_id} has been cancelled. Please rebook."
        }
    else:
        print("Invalid choice")
        return
    
    result = call_notification_agent_http(endpoint="/simulate", payload=payload)
    
    if "error" not in result:
        print(f"\n {result.get('message')}")
        print("   Run 'Check Notifications' to see it!")


def workflow_list_bookings():
    """WORKFLOW 4: List all current bookings."""
    print("\n" + "="*60)
    print(" WORKFLOW: List All Bookings")
    print("="*60)
    
    try:
        response = requests.get(f"{BOOKING_AGENT_URL}/bookings", timeout=10)
        data = response.json()
    except Exception as e:
        print(f" Error: {e}")
        return
    
    bookings = data.get("bookings", [])
    if not bookings:
        print("\n No bookings yet. Try the 'Search and Book' workflow!")
        return
    
    print(f"\n📋 Total bookings: {len(bookings)}\n")
    for b in bookings:
        status_emoji = {"confirmed": "Success", "cancelled": "Failed"}.get(b["status"], "❓")
        print(f"  {status_emoji} {b['booking_id']} | {b['passenger_name']}")
        print(f"     Flight: {b['flight_id']} | ${b['price']} | {b['status'].upper()}")
        print(f"     Booked: {b['booked_at']}\n")


# ══════════════════════════════════════════════════════════════════════════
# MAIN MENU
# ══════════════════════════════════════════════════════════════════════════

def main():
    """
    Interactive CLI for running orchestrated workflows.
    Shows a menu and runs the selected workflow.
    """
    print("\n" + " " * 20)
    print("  FLIGHT BOOKING MULTI-AGENT ORCHESTRATOR")
    print(" " * 20)
    print("\nThis orchestrator coordinates 3 agents:")
    print("  Search Agent    (STDIO)   — finds flights")
    print("  Booking Agent   (HTTP)    — books flights")
    print("  Notification    (Webhook) — tracks changes")
    print("\nMake sure all agents are running before using this!")
    print("  Terminal 1: python agents/search_agent/server.py  (optional — STDIO is auto-launched)")
    print("  Terminal 2: python agents/booking_agent/server.py")
    print("  Terminal 3: python agents/notification_agent/server.py")
    
    while True:
        print("\n" + "─"*40)
        print("MENU:")
        print("  1. Search and Book a Flight (full workflow)")
        print("  2. Check Notifications")
        print("  3. Simulate a Webhook Event")
        print("  4. List All Bookings")
        print("  5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == "1":
            print("\nLet's search and book a flight!")
            origin      = input("  Origin airport code (e.g. JFK): ").strip().upper() or "JFK"
            destination = input("  Destination code   (e.g. LAX): ").strip().upper() or "LAX"
            date        = input("  Travel date (YYYY-MM-DD):      ").strip() or "2025-02-01"
            name        = input("  Your name:                     ").strip() or "Test User"
            email       = input("  Your email:                    ").strip() or "test@example.com"
            
            workflow_search_and_book(origin, destination, date, name, email)
        
        elif choice == "2":
            workflow_check_notifications()
        
        elif choice == "3":
            workflow_simulate_event()
        
        elif choice == "4":
            workflow_list_bookings()
        
        elif choice == "5":
            print("\n👋 Goodbye!\n")
            break
        
        else:
            print("Invalid choice. Enter 1-5.")


if __name__ == "__main__":
    main()
