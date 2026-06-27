"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
config/settings.py — Central Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT IS THIS FILE?
  One place for ALL configuration values used across the project.
  Every port number, URL, API key, timeout — defined here.

WHY CENTRAL CONFIG?
  ✓ Change a port in ONE place, not hunting through 5 files
  ✓ Easy to switch between dev/staging/prod environments
  ✓ Clear overview of all configuration the app needs

IN PRODUCTION:
  You'd use environment-specific config files:
  config/dev.py, config/prod.py, config/test.py
  and load the right one based on ENV variable.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# External APIs
AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY", "")
AVIATIONSTACK_BASE_URL = "http://api.aviationstack.com/v1"

# Agent Ports
BOOKING_AGENT_PORT      = int(os.getenv("BOOKING_AGENT_PORT", "8001"))
NOTIFICATION_AGENT_PORT = int(os.getenv("NOTIFICATION_AGENT_PORT", "8002"))

# Agent URLs (used by orchestrator)
BOOKING_AGENT_URL      = f"http://localhost:{BOOKING_AGENT_PORT}"
NOTIFICATION_AGENT_URL = f"http://localhost:{NOTIFICATION_AGENT_PORT}"

# Webhook Security 
# Shared secret between us and external services for verifying webhooks
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "changeit")

# ── Timeouts (seconds) 
HTTP_TIMEOUT    = 10
STDIO_TIMEOUT   = 30

# Feature Flags
# Automatically use real API if key is set, otherwise mock
USE_REAL_API = bool(AVIATIONSTACK_API_KEY and AVIATIONSTACK_API_KEY != "YOUR_KEY_HERE")

# Database Adapter
# "json"     = use local flights.json (default, no setup needed)
# "postgres" = use PostgreSQL (configure DB_* vars below)
USE_DB = os.getenv("USE_DB", "json")
