# Flight Booking Multi-Agent System
### Learn MCP with STDIO + HTTP + Webhooks — all in one project

---

## 🗺️ What we are Building

A system of **3 AI agents** that coordinate to search, book, and track flights.
Each agent uses a **different transport type** so you learn all three at once.

```
You (Claude Desktop or CLI)
        │
        ▼
  ┌─────────────────┐
  │   Orchestrator  │  ← coordinates everything
  └────────┬────────┘
           │
    ┌──────┼──────┐
    │      │      │
    ▼      ▼      ▼
  STDIO   HTTP  Webhook
    │      │      │
 Search  Book  Notify
 Agent   Agent  Agent
```

## Setup — Step by Step

### Step 1: Install dependencies

```bash
# Navigate to the project
cd flight-booking-agents

# Install all Python packages
pip install -r requirements.txt
```

### Step 2: Set up your environment file

```bash
# Copy the template
cp .env.example .env

# Open .env in any text editor and optionally add your AviationStack key
# The project works WITHOUT the key using mock data
```

### Step 3: Configure Claude Desktop (for STDIO agent)

1. Find your Claude Desktop config file:
   - **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

2. Copy the contents of `claude_desktop_config.json` from this project into it

3. **Replace** `/path/to/your/project` with your actual project path:
   ```json
   "args": ["/Users/yourname/projects/flight-booking-agents/agents/search_agent/server.py"]
   ```

4. Quit and reopen Claude Desktop

5. You should see "flight-search-agent" in Claude's tool panel

---

## Running the System

### Terminal 1 — Booking Agent (HTTP on port 8001)
```bash
cd flight-booking-agents/agents/booking_agent
python server.py

# we will see:
# Starting Booking Agent HTTP Server...
# API Docs available at: http://localhost:8001/docs
```

### Terminal 2 — Notification Agent (Webhook on port 8002)
```bash
cd flight-booking-agents/agents/notification_agent
python server.py

# we will see:
# Starting Notification Agent (Webhook Server)...
# API Docs: http://localhost:8002/docs
```

### Terminal 3 — Orchestrator (coordinates all agents)
```bash
cd flight-booking-agents
python orchestrator/main.py

# # we will see an interactive menu
```

> The Search Agent (STDIO) is launched automatically — no separate terminal needed for it.

---

## Testing Each Transport

### Test 1: STDIO (Search Agent)
The easiest way is through Claude Desktop — just ask:
> "Search for flights from JFK to LAX on 2025-02-01"

Or via the Orchestrator CLI → select option 1.

### Test 2: HTTP (Booking Agent)
```bash
# Health check
curl http://localhost:8001/

# Search bookings
curl http://localhost:8001/bookings

# Book a flight
curl -X POST http://localhost:8001/book \
  -H "Content-Type: application/json" \
  -d '{"flight_id": "AA101", "passenger_name": "Nihar", "email": "Nihar@test.com"}'

# Cancel a booking (use a real booking_id from above)
curl -X POST http://localhost:8001/cancel \
  -H "Content-Type: application/json" \
  -d '{"booking_id": "BK-AA101-XXXXX"}'
```

Or open **http://localhost:8001/docs** in your browser — interactive API playground!

### Test 3: Webhooks (Notification Agent)
```bash
# Simulate a price drop webhook
curl -X POST http://localhost:8002/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "price_drop",
    "flight_id": "AA101",
    "old_price": 299.99,
    "new_price": 199.99,
    "message": "Price dropped by $100!"
  }'

# Check your notifications
curl http://localhost:8002/notifications

# Simulate a delay
curl -X POST http://localhost:8002/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "delay",
    "flight_id": "UA202",
    "delay_minutes": 45,
    "message": "Flight UA202 delayed by 45 minutes"
  }'
```

Or open **http://localhost:8002/docs** — same interactive playground!

---

## Adding the Real AviationStack API

### Step 1: Get your free API key
1. Go to https://aviationstack.com
2. Click "Get Free API Key" (100 API calls/month)
3. Sign up (no credit card needed)
4. Copy your API key

### Step 2: Add it to your .env file
```bash
# Open .env and change this line:
AVIATIONSTACK_API_KEY=YOUR_KEY_HERE

# To your real key:
AVIATIONSTACK_API_KEY=abc123xyz456yourrealkey
```

### Step 3: That's it!
The Search Agent automatically detects the key and switches from mock data to real API.
No code changes needed.

---

## Real Webhooks with ngrok

Want a real external service to send you webhooks? Use ngrok:

```bash
# Install ngrok
brew install ngrok  # Mac
# or download from https://ngrok.com

# Start your Notification Agent
python agents/notification_agent/server.py

# In another terminal, expose it publicly
ngrok http 8002

# ngrok gives you a public URL like:
# https://abc123.ngrok.io

# Give this URL to any service:
# https://abc123.ngrok.io/webhook
```

---

## Key Concepts Summary

### What is MCP?
**Model Context Protocol** — a standard way for AI models (like Claude) to discover and call external tools. Instead of each AI company inventing their own tool format, MCP is the universal standard.

### What is a Tool?
A function that Claude can call. Each tool has:
- `name` — how Claude refers to it
- `description` — Claude reads this to know when to use it
- `inputSchema` — what arguments it accepts

### What is an Agent?
A service that exposes tools. It has a transport (how it communicates) and a set of tools (what it can do).

### What is Orchestration?
Coordinating multiple agents to complete a multi-step task. The Orchestrator knows which agent to call, passes results between them, and handles the overall flow.

---

## Troubleshooting

**Claude Desktop doesn't show my agents:**
- Make sure you edited the right config file (path varies by OS)
- Fully quit Claude Desktop (⌘Q on Mac, not just close window)
- Check that your Python path in the config is correct

**Booking Agent connection refused:**
- Make sure you ran `python agents/booking_agent/server.py` first
- Check port 8001 isn't used by something else: `lsof -i :8001`

**Import errors when running servers:**
- Run `pip install -r requirements.txt` again
- Make sure you're in the right Python environment

**AviationStack returns no flights:**
- Free tier only shows live/active flights right now
- Try without a date, or use mock data (remove API key from .env)

STDIO   = a tool you pick up and use locally
          like a calculator on your desk

HTTP    = a service you call when you need it
          like calling a restaurant to order food

Webhook = a doorbell someone else rings
          you don't call them — they notify you

What __init__.py does
It tells Python "this folder is a package" — meaning you can import from it like a module.
Without __init__.py:
pythonfrom agents.search_agent.tools import search_flights
# ❌ ERROR — Python doesn't know agents/ is a package
With __init__.py:
pythonfrom agents.search_agent.tools import search_flights
# ✅ Works — Python recognizes agents/ as a package
flight-booking-agents/
├── agents/
│   ├── __init__.py              ← "agents/ is a package"
│   ├── search_agent/
│   │   ├── __init__.py          ← "search_agent/ is a package"
│   │   ├── server.py
│   │   └── tools.py
│   ├── booking_agent/
│   │   ├── __init__.py          ← "booking_agent/ is a package"
│   │   ├── server.py
│   │   └── tools.py
├── shared/
│   ├── __init__.py              ← "shared/ is a package"
│   ├── models.py
│   └── database.py
├── config/
│   ├── __init__.py              ← "config/ is a package"
│   └── settings.py


With Adapters
flight-booking-agents/
├── agents/
│   ├── search_agent/
│   │   ├── server.py
│   │   ├── tools.py
│   │   └── adapters/          ← should exist!
│   │       ├── mock_adapter.py      ← reads flights.json
│   │       └── aviationstack_adapter.py  ← calls real API
│   │
│   ├── booking_agent/
│   │   ├── server.py
│   │   ├── tools.py
│   │   └── adapters/          ← should exist!
│   │       ├── json_adapter.py      ← saves to JSON file
│   │       └── postgres_adapter.py  ← saves to real DB


Architecture View
USER/CLAUDE
    │
    │  (HTTP request / STDIO message / Webhook POST)
    ▼
SERVER.PY          ← receives the request
    │
    │  calls book_flight(request)
    ▼
TOOLS.PY           ← decides what to do
    │
    │  calls adapter.create_booking(...)
    ▼
ADAPTER            ← talks to data source
    │
    │  reads/writes to DB or API
    ▼
DATA SOURCE        ← flights.json / PostgreSQL / AviationStack
    │
    │  returns data back
    ▼
ADAPTER            ← returns result to tools
    │
    ▼
TOOLS.PY           ← returns result to server
    │
    ▼
SERVER.PY          ← sends response back to user
    │
    ▼
USER/CLAUDE        ← sees the result