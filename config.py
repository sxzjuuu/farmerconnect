import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Application configuration with sensible production/development defaults."""

    # Flask Configuration
    SECRET_KEY = os.getenv("SECRET_KEY", "farmerconnect-secret-key-college-demo-2026")
    DEBUG = os.getenv("FLASK_DEBUG", "0") in ("1", "true", "True")
    TESTING = False

    # Database Configuration
    DB_NAME = os.getenv("DATABASE_PATH", "farmerconnect.db")
    DB_PATH = str(BASE_DIR / DB_NAME)

    # External APIs
    DATA_GOV_IN_API_KEY = os.getenv("DATA_GOV_IN_API_KEY", "").strip()
    DATA_GOV_IN_RESOURCE_ID = os.getenv(
        "DATA_GOV_IN_RESOURCE_ID", "9ef84268-d588-465a-a308-a864a43d0070"
    ).strip()
    DATA_GOV_IN_BASE_URL = "https://api.data.gov.in/resource"

    OPEN_METEO_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
    OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

    # Default Geographic Context (Tamil Nadu, India)
    DEFAULT_LOCATION_NAME = os.getenv("DEFAULT_LOCATION_NAME", "Coimbatore")
    DEFAULT_STATE = "Tamil Nadu"
    DEFAULT_LATITUDE = float(os.getenv("DEFAULT_LATITUDE", "11.0055"))
    DEFAULT_LONGITUDE = float(os.getenv("DEFAULT_LONGITUDE", "76.9661"))

    # Request timeouts (in seconds)
    REQUEST_TIMEOUT = 8

    # Cache expiration (in seconds)
    WEATHER_CACHE_TTL = 600  # 10 minutes
    MARKET_CACHE_TTL = 3600  # 1 hour


class TestConfig(Config):
    """Configuration for automated test suite."""

    TESTING = True
    DEBUG = False
    DB_NAME = "test_farmerconnect.db"
    DB_PATH = str(BASE_DIR / "test_farmerconnect.db")

