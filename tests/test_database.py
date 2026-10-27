"""Tests for SQLite database module, schema, indexes, and queries."""

import database


def test_init_db(test_db_path):
    """Test tables and indexes exist after database initialization."""
    with database.get_db_connection(test_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]

        assert "market_prices" in tables
        assert "saved_locations" in tables
        assert "price_history" in tables

        # Verify indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
        indexes = [row[0] for row in cursor.fetchall()]
        assert "idx_market_prices_query" in indexes
        assert "idx_price_history_crop_market" in indexes


def test_seed_demo_data(test_db_path):
    """Test seeding demo data inserts expected records and is idempotent."""
    # Seed already done in fixture; calling without force should return 0 (no duplicates)
    n = database.seed_demo_data(db_path=test_db_path, force=False)
    assert n == 0


def test_save_market_prices_duplicate_prevention(test_db_path):
    """Test duplicate insertion updates price without creating duplicate rows."""
    records = [
        {
            "crop_name": "TestCropUnique",
            "variety": "Local",
            "state": "Tamil Nadu",
            "district": "Coimbatore",
            "market_name": "Coimbatore Market",
            "min_price": 2500,
            "max_price": 3200,
            "modal_price": 2800,
            "price_unit": "₹/Quintal",
            "arrival_date": "2026-10-27",
            "source_name": "Test Source",
            "source_type": "LIVE",
        }
    ]

    saved1 = database.save_market_prices(records, db_path=test_db_path)
    assert saved1 == 1

    # Insert same record with updated modal price
    records[0]["modal_price"] = 2950
    saved2 = database.save_market_prices(records, db_path=test_db_path)
    assert saved2 == 1

    # Verify only one row exists with updated modal price
    with database.get_db_connection(test_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*), modal_price FROM market_prices WHERE crop_name = 'TestCropUnique' AND source_type = 'LIVE';"
        )
        row = cursor.fetchone()
        assert row[0] == 1
        assert row[1] == 2950


def test_saved_locations(test_db_path):
    """Test saving and retrieving default location."""
    database.save_location(
        location_name="Salem_Test",
        latitude=11.6643,
        longitude=78.1460,
        district="Salem",
        is_default=1,
        db_path=test_db_path,
    )

    def_loc = database.get_default_location(db_path=test_db_path)
    assert def_loc["location_name"] == "Salem_Test"
    assert def_loc["latitude"] == 11.6643
