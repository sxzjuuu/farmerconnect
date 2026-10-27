"""Tests for Flask application routes and API endpoints."""

import json


def test_health_endpoint(client):
    """Test /api/health endpoint returns 200 with service metadata."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["service"] == "FarmerConnect"
    assert "provider_mode" in data


def test_home_page_route(client):
    """Test dashboard index page renders successfully."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "FarmerConnect" in html
    assert "Dashboard" in html


def test_weather_page_route(client):
    """Test /weather page renders with expected elements."""
    response = client.get("/weather")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Live Agricultural Weather" in html
    assert "Tamil Nadu" in html


def test_markets_page_route(client):
    """Test /markets page renders with price tables."""
    response = client.get("/markets")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Mandi Market Prices" in html


def test_compare_page_route(client):
    """Test /compare page renders with mandi comparison tools."""
    response = client.get("/compare")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Mandi Price Comparison Tool" in html
    assert "Transit Cost" in html


def test_history_page_route(client):
    """Test /history page renders with trend chart containers."""
    response = client.get("/history")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Price Trend Analysis" in html
    assert "historySvgChart" in html


def test_about_page_route(client):
    """Test /about page renders with academic documentation."""
    response = client.get("/about")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Abstract" in html
    assert "Viva Questions" in html


def test_404_error_handler(client):
    """Test non-existent routes return 404 status."""
    html_resp = client.get("/non-existent-page-url")
    assert html_resp.status_code == 404

    api_resp = client.get("/api/non-existent-endpoint")
    assert api_resp.status_code == 404
    data = api_resp.get_json()
    assert data["status"] == "error"


def test_select_location_api(client):
    """Test POST /api/locations/select updates default location."""
    payload = {
        "location_name": "Tiruppur",
        "latitude": 11.1085,
        "longitude": 77.3411,
        "district": "Tiruppur",
    }
    resp = client.post(
        "/api/locations/select",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["location"]["location_name"] == "Tiruppur"


def test_select_location_api_invalid(client):
    """Test POST /api/locations/select rejects invalid coordinates."""
    invalid_payload = {
        "location_name": "Invalid Place",
        "latitude": 999.0,  # Invalid latitude > 90
        "longitude": 77.0,
    }
    resp = client.post(
        "/api/locations/select",
        data=json.dumps(invalid_payload),
        content_type="application/json",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
