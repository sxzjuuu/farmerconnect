"""Tests for weather service and endpoints."""

from unittest.mock import patch
import requests
from weather_service import get_weather_forecast, search_locations, validate_coordinates


def test_coordinate_validation():
    """Test latitude and longitude boundary checks."""
    valid, _ = validate_coordinates(11.0055, 76.9661)
    assert valid is True

    valid, err = validate_coordinates(95.0, 76.0)
    assert valid is False
    assert "Latitude must be between -90 and 90" in err

    valid, err = validate_coordinates(11.0, 200.0)
    assert valid is False
    assert "Longitude must be between -180 and 180" in err

    valid, err = validate_coordinates("invalid", "coords")
    assert valid is False


def test_location_search_tamil_nadu_fallback():
    """Test location search resolves major Tamil Nadu agricultural hubs."""
    results = search_locations("Coimbatore")
    assert len(results) > 0
    assert any("Coimbatore" in r["name"] for r in results)

    results_erode = search_locations("Erode")
    assert len(results_erode) > 0
    assert any("Erode" in r["name"] for r in results_erode)


def test_weather_endpoint_success(client):
    """Test /api/weather endpoint with default and query parameters."""
    response = client.get("/api/weather?location=Coimbatore")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert "current" in data["data"]
    assert "forecast" in data["data"]
    assert "temperature" in data["data"]["current"]
    assert len(data["data"]["forecast"]) <= 5


def test_weather_endpoint_invalid_coordinates(client):
    """Test /api/weather rejects invalid latitude/longitude."""
    response = client.get("/api/weather?lat=999.0&lon=77.0")
    assert response.status_code == 400
    data = response.get_json()
    assert data["status"] == "error"


def test_weather_endpoint_timeout_handling():
    """Test weather service handles timeout gracefully."""
    with patch("requests.get", side_effect=requests.Timeout):
        result = get_weather_forecast(11.0055, 76.9661, force_refresh=True)
        assert result["status"] == "error"
        assert "timed out" in result["message"]


def test_weather_endpoint_api_failure_handling():
    """Test weather service handles external HTTP error codes gracefully."""
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 500
        mock_get.return_value.text = "Internal Server Error"
        result = get_weather_forecast(11.0055, 76.9661, force_refresh=True)
        assert result["status"] == "error"
        assert "error status 500" in result["message"]
