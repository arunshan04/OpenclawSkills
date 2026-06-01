"""
Run this once in the Codespace to fix the Weather Forecast skill's tool code.

Usage:
    cd skills-registry/backend
    python3 ../fix_weather_tools.py
"""
import httpx, sys

BASE = "http://localhost:8000"

get_current_weather_code = '''\
def get_current_weather(city_name: str) -> str:
    geo = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city_name, "count": 1},
        timeout=10,
    )
    geo.raise_for_status()
    results = geo.json().get("results")
    if not results:
        return f"City \'{city_name}\' not found."
    loc = results[0]
    lat, lon = loc["latitude"], loc["longitude"]

    wx = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
            "timezone": "auto",
        },
        timeout=10,
    )
    wx.raise_for_status()
    c = wx.json()["current"]
    return (
        f"Weather in {loc[\'name\']}, {loc.get(\'country\', \'\')}:\\n"
        f"Temperature : {c[\'temperature_2m\']}°C (feels like {c[\'apparent_temperature\']}°C)\\n"
        f"Humidity    : {c[\'relative_humidity_2m\']}%\\n"
        f"Wind        : {c[\'wind_speed_10m\']} km/h\\n"
        f"Precipitation: {c[\'precipitation\']} mm\\n"
        f"Code        : {c[\'weather_code\']}"
    )
'''

get_5day_forecast_code = '''\
def get_5day_forecast(city_name: str) -> str:
    geo = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city_name, "count": 1},
        timeout=10,
    )
    geo.raise_for_status()
    results = geo.json().get("results")
    if not results:
        return f"City \'{city_name}\' not found."
    loc = results[0]
    lat, lon = loc["latitude"], loc["longitude"]

    fc = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
            "forecast_days": 5,
            "timezone": "auto",
        },
        timeout=10,
    )
    fc.raise_for_status()
    daily = fc.json()["daily"]
    lines = [f"5-Day Forecast for {loc[\'name\']}, {loc.get(\'country\', \'\')}:"]
    for i in range(5):
        lines.append(
            f"  {daily[\'time\'][i]}: "
            f"High {daily[\'temperature_2m_max\'][i]}°C / Low {daily[\'temperature_2m_min\'][i]}°C | "
            f"Rain {daily[\'precipitation_sum\'][i]} mm | Code {daily[\'weather_code\'][i]}"
        )
    return "\\n".join(lines)
'''

city_name_schema = {
    "type": "object",
    "properties": {"city_name": {"type": "string", "description": "Name of the city"}},
    "required": ["city_name"],
}

with httpx.Client(timeout=10) as c:
    # Find Weather Forecast skill
    skills = c.get(f"{BASE}/skills").json()
    weather = next((s for s in skills if "weather" in s["name"].lower()), None)
    if not weather:
        print("ERROR: No weather skill found in registry.")
        sys.exit(1)

    skill_id = weather["id"]
    print(f"Found: {weather['name']}  id={skill_id}")

    # Patch tools
    r = c.put(f"{BASE}/skills/{skill_id}", json={
        "tools": [
            {"name": "get_current_weather", "description": "Get current weather conditions for a city",
             "input_schema": city_name_schema, "code": get_current_weather_code},
            {"name": "get_5day_forecast",   "description": "Get a 5-day weather forecast for a city",
             "input_schema": city_name_schema, "code": get_5day_forecast_code},
        ]
    })

    if r.is_success:
        s = r.json()
        print("Updated:", s["name"])
        for t in s["tools"]:
            keys = list(t.get("input_schema", {}).get("properties", {}).keys())
            has_code = bool((t.get("code") or "").strip())
            print(f"  {t['name']}  params={keys}  has_code={has_code}")
        print("\nDone. Restart the backend to reload MCP tools:")
        print("  pkill -f uvicorn && uvicorn main:app --host 0.0.0.0 --port 8000 &")
    else:
        print("ERROR:", r.status_code, r.text[:300])
        sys.exit(1)
