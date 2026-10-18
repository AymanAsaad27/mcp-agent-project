
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather-server")

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SECONDS = 15


@mcp.tool()
def get_weather(city: str) -> dict[str, Any]:
    """Get current weather conditions for a city using Open-Meteo."""
    city = city.strip()

    if not city:
        raise ValueError("City name cannot be empty.")

    if len(city) > 100:
        raise ValueError("City name is too long.")

    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        # Step 1: Convert the city name into coordinates.
        geo_response = client.get(
            GEOCODING_URL,
            params={
                "name": city,
                "count": 1,
                "language": "en",
                "format": "json",
            },
        )
        geo_response.raise_for_status()
        geo_data = geo_response.json()

        results = geo_data.get("results") or []
        if not results:
            raise ValueError(f"No location found for city: {city}")

        location = results[0]
        latitude = location["latitude"]
        longitude = location["longitude"]

        # Step 2: Retrieve current weather for those coordinates.
        weather_response = client.get(
            WEATHER_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,"
                    "relative_humidity_2m,"
                    "apparent_temperature,"
                    "is_day,"
                    "precipitation,"
                    "weather_code,"
                    "wind_speed_10m"
                ),
                "timezone": "auto",
            },
        )
        weather_response.raise_for_status()
        weather_data = weather_response.json()

    current = weather_data.get("current")
    if not current:
        raise ValueError("Weather data did not include current conditions.")

    return {
        "location": {
            "name": location.get("name"),
            "country": location.get("country"),
            "latitude": latitude,
            "longitude": longitude,
            "timezone": weather_data.get("timezone"),
        },
        "current": current,
        "units": weather_data.get("current_units", {}),
        "source": "Open-Meteo",
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
