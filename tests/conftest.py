"""Pytest configuration and shared fixtures for FarmerConnect tests."""

import os
from pathlib import Path
import pytest
from app import create_app
from config import TestConfig
import database

TEST_DB_PATH = TestConfig.DB_PATH


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Ensure clean test database before test session and cleanup after."""
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass

    database.init_db(TEST_DB_PATH)
    database.seed_demo_data(TEST_DB_PATH, force=True)

    yield

    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass


@pytest.fixture
def app():
    """Create and configure an isolated Flask app instance for testing."""
    test_app = create_app(TestConfig)
    return test_app


@pytest.fixture
def client(app):
    """Test client for HTTP requests."""
    return app.test_client()


@pytest.fixture
def test_db_path():
    """Return the test database path."""
    return TEST_DB_PATH
