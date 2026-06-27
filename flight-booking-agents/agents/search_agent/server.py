import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from agents.search_agent.tools import search_flights, get_flight_price

# Create the MCP server — name shown in Claude Desktop UI
server = Server("flight-search-agent")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """
    Called by Claude Desktop on startup to discover available tools.
    Returns tool definitions — name, description, and input schema.
    Claude reads the description to know WHEN to use each tool.
    """
    return [
        types.Tool(
            name="search_flights",
            description=(
                "Search for available flights between two airports on a given date. "
                "Returns airline, departure/arrival times, prices and seat availability. "
                "Use 3-letter IATA airport codes: JFK, LAX, LHR, CDG, DXB, SIN, etc."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "origin":      {"type": "string", "description": "Departure IATA code (e.g. JFK)"},
                    "destination": {"type": "string", "description": "Arrival IATA code (e.g. LAX)"},
                    "date":        {"type": "string", "description": "Travel date YYYY-MM-DD"}
                },
                "required": ["origin", "destination", "date"]
            }
        ),
        types.Tool(
            name="get_flight_price",
            description=(
                "Get detailed pricing and seat availability for a specific flight by its ID. "
                "Use after search_flights to get more detail on a particular option."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "flight_id": {"type": "string", "description": "Flight ID from search results (e.g. AA101)"}
                },
                "required": ["flight_id"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """
    Called every time Claude invokes one of our tools.
    Routes to the correct function in tools.py.
    """
    if name == "search_flights":
        result = search_flights(
            origin=arguments["origin"],
            destination=arguments["destination"],
            date=arguments["date"]
        )

        if not result.flights:
            text = f"No flights found from {arguments['origin']} to {arguments['destination']} on {arguments['date']}."
        else:
            lines = [f"Found {result.count} flight(s) [{result.source} data]:\n"]
            for i, f in enumerate(result.flights, 1):
                lines.append(
                    f"{i}.  {f.airline} | Flight {f.flight_id}\n"
                    f"   {f.departure} → {f.arrival}\n"
                    f"   ${f.price:.2f} | {f.seats_available} seats left\n"
                )
            text = "\n".join(lines)

    elif name == "get_flight_price":
        result = get_flight_price(arguments["flight_id"])
        if not result["found"]:
            text = result["message"]
        else:
            text = (
                f"💰 Price for {result['flight_id']}:\n"
                f"   Airline: {result['airline']}\n"
                f"   Route:   {result['route']}\n"
                f"   Class:   {result['seat_class']}\n"
                f"   Price:   ${result['price']:.2f}\n"
                f"   Seats:   {result['seats_remaining']} left\n"
            )
    else:
        text = f"Unknown tool: {name}"

    return [types.TextContent(type="text", text=text)]


async def main():
    """Start the STDIO MCP server. Runs until Claude Desktop closes the connection."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
