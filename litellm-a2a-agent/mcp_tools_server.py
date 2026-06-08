"""
A small MCP server exposing a handful of real tools over streamable-HTTP.

Tools:
  - add(a, b)            -> sum of two numbers
  - multiply(a, b)       -> product of two numbers
  - word_count(text)     -> number of words in text
  - current_time()       -> current UTC time (ISO-8601)
  - weather(city)        -> mock weather report for a city

Run:
  python mcp_tools_server.py            # serves streamable-HTTP at /mcp on :9200
"""
import datetime
import os

from mcp.server.fastmcp import FastMCP

PORT = int(os.environ.get("MCP_PORT", "9200"))

# streamable_http_path defaults to "/mcp"; bind to all interfaces on PORT.
mcp = FastMCP("litellm-demo-tools", host="0.0.0.0", port=PORT)


@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers and return the sum."""
    return a + b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers and return the product."""
    return a * b


@mcp.tool()
def word_count(text: str) -> int:
    """Return the number of whitespace-separated words in text."""
    return len(text.split())


@mcp.tool()
def current_time() -> str:
    """Return the current UTC time in ISO-8601 format."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


@mcp.tool()
def weather(city: str) -> str:
    """Return a (mock) current weather report for the given city."""
    # Deterministic pseudo-weather so the demo is stable.
    conditions = ["sunny", "cloudy", "rainy", "windy", "clear"]
    temp = 15 + (sum(ord(c) for c in city) % 16)  # 15-30 C
    cond = conditions[sum(ord(c) for c in city) % len(conditions)]
    return f"Weather in {city}: {cond}, {temp}°C (demo data)."


if __name__ == "__main__":
    # FastMCP runs uvicorn internally for the streamable-http transport.
    mcp.run(transport="streamable-http")
