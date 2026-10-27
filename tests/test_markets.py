"""Tests for agricultural market service and endpoints."""

from market_service import MarketService, DataGovInMarketProvider


def test_market_endpoint_all(client):
    """Test /api/markets returns list of market prices."""
    response = client.get("/api/markets")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert "records" in data
    assert len(data["records"]) > 0


def test_market_endpoint_crop_filter(client):
    """Test /api/markets filters accurately by crop name."""
    response = client.get("/api/markets?crop=Tomato")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    records = data["records"]
    assert len(records) > 0
    assert all("Tomato" in r["crop_name"] for r in records)


def test_market_endpoint_district_filter(client):
    """Test /api/markets filters by district."""
    response = client.get("/api/markets?district=Coimbatore")
    assert response.status_code == 200
    data = response.get_json()
    records = data["records"]
    assert len(records) > 0
    assert all(r["district"] == "Coimbatore" for r in records)


def test_market_endpoint_sorting(client):
    """Test /api/markets sorting modal price ascending and descending."""
    # Ascending
    resp_asc = client.get("/api/markets?sort=price_asc&limit=10")
    prices_asc = [r["modal_price"] for r in resp_asc.get_json()["records"]]
    assert prices_asc == sorted(prices_asc)

    # Descending
    resp_desc = client.get("/api/markets?sort=price_desc&limit=10")
    prices_desc = [r["modal_price"] for r in resp_desc.get_json()["records"]]
    assert prices_desc == sorted(prices_desc, reverse=True)


def test_market_endpoint_empty_results(client):
    """Test searching for non-existent crop returns empty records list."""
    response = client.get("/api/markets?crop=NonExistentCrop12345")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["records"]) == 0
    assert data["pagination"]["total_records"] == 0


def test_market_source_labeling(client):
    """Test all records contain transparent source_type and source_name."""
    response = client.get("/api/markets?limit=10")
    records = response.get_json()["records"]
    for r in records:
        assert r["source_type"] in ("LIVE", "DEMO")
        assert len(r["source_name"]) > 0


def test_market_compare_endpoint(client):
    """Test /api/markets/compare computes highest, lowest, and price spread."""
    response = client.get("/api/markets/compare?crop=Tomato")
    assert response.status_code == 200
    data = response.get_json()
    assert data["crop"] == "Tomato"
    assert data["highest_market"] is not None
    assert data["lowest_market"] is not None
    assert data["max_price_spread"] >= 0
    assert "disclaimer" in data
    # Verify spread calculation
    expected_spread = round(data["highest_market"]["modal_price"] - data["lowest_market"]["modal_price"], 2)
    assert data["max_price_spread"] == expected_spread


def test_price_history_endpoint(client):
    """Test /api/markets/history returns chronological price observations."""
    response = client.get("/api/markets/history?crop=Tomato")
    assert response.status_code == 200
    data = response.get_json()
    assert "observations" in data
    assert len(data["observations"]) > 0
    assert data["summary"] is not None
    assert "avg_recorded" in data["summary"]
    assert "percentage_change" in data["summary"]


def test_filter_options_endpoint(client):
    """Test /api/markets/filters returns lists of available crops and districts."""
    response = client.get("/api/markets/filters")
    assert response.status_code == 200
    data = response.get_json()
    assert "crops" in data
    assert "districts" in data
    assert "Tomato" in data["crops"]
    assert "Coimbatore" in data["districts"]


def test_provider_fallback_mode():
    """Test DataGovInMarketProvider returns demo fallback notice when unconfigured."""
    provider = DataGovInMarketProvider(api_key="")
    assert provider.is_configured() is False
    res = provider.fetch_market_prices(crop="Tomato")
    assert res["success"] is False
    assert "Demonstration Mode" in res["error_message"]
