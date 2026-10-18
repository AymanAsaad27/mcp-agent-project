
from servers.weather_server import get_weather


def main():
    print("\n1. TEST CITY INPUT VALIDATION")

    try:
        get_weather("   ")
    except ValueError as exc:
        print("Correctly rejected empty city:", exc)
    else:
        raise AssertionError("Empty city was not rejected")

    print("\n2. FETCH CURRENT WEATHER")

    try:
        result = get_weather("Singapore")
    except Exception as exc:
        print(f"Weather API test failed: {type(exc).__name__}: {exc}")
        raise

    print("Location:", result["location"])
    print("Current conditions:", result["current"])
    print("Units:", result["units"])
    print("Source:", result["source"])

    assert result["location"]["name"]
    assert "temperature_2m" in result["current"]
    assert result["source"] == "Open-Meteo"

    print("\nAll weather direct tests passed.")


if __name__ == "__main__":
    main()
