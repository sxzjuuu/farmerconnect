"""Market Service for FarmerConnect.

Provides an extensible abstraction for agricultural market price data.
Includes:
- BaseMarketProvider interface.
- DataGovInMarketProvider for India's official data.gov.in (Agmarknet) API.
- Fallback / Database querying with transparent LIVE vs DEMO labeling.
- Duplicate prevention and persistent price observation recording.
- Statistical calculations for market comparisons and price history.
"""

import abc
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import requests

from config import Config
import database

logger = logging.getLogger(__name__)


class BaseMarketProvider(abc.ABC):
    """Abstract base class for agricultural market data providers."""

    @abc.abstractmethod
    def fetch_market_prices(
        self,
        crop: Optional[str] = None,
        district: Optional[str] = None,
        market: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Fetch market prices from the external provider.

        Returns a dictionary with:
        - success (bool)
        - records (List[Dict])
        - total (int)
        - error_message (Optional[str])
        - source_name (str)
        - source_type (str: 'LIVE' or 'DEMO')
        """
        pass

    @abc.abstractmethod
    def is_configured(self) -> bool:
        """Check if provider credentials and endpoints are configured."""
        pass


class DataGovInMarketProvider(BaseMarketProvider):
    """Provider for India's official Open Government Data (data.gov.in).

    Uses the Agmarknet agricultural commodity daily market-price dataset.
    Endpoint: https://api.data.gov.in/resource/{resource_id}
    """

    def __init__(self, api_key: Optional[str] = None, resource_id: Optional[str] = None):
        self.api_key = api_key if api_key is not None else Config.DATA_GOV_IN_API_KEY
        self.resource_id = resource_id if resource_id is not None else Config.DATA_GOV_IN_RESOURCE_ID
        self.base_url = Config.DATA_GOV_IN_BASE_URL

    def is_configured(self) -> bool:
        """Return True if an API key is present."""
        return bool(self.api_key and len(self.api_key.strip()) > 8)

    def fetch_market_prices(
        self,
        crop: Optional[str] = None,
        district: Optional[str] = None,
        market: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Fetch live records from data.gov.in."""
        if not self.is_configured():
            return {
                "success": False,
                "records": [],
                "total": 0,
                "error_message": (
                    "Official data.gov.in API key not configured. "
                    "Running in Demonstration Mode with realistic Tamil Nadu agricultural data."
                ),
                "source_name": "data.gov.in (Agmarknet)",
                "source_type": "LIVE",
            }

        url = f"{self.base_url}/{self.resource_id}"
        params: Dict[str, Any] = {
            "api-key": self.api_key,
            "format": "json",
            "limit": max(1, min(limit, 100)),
            "offset": max(0, offset),
            "filters[state]": Config.DEFAULT_STATE,  # Default to Tamil Nadu
        }

        if crop and crop.strip():
            params["filters[commodity]"] = crop.strip()
        if district and district.strip() and district.lower() != "all":
            params["filters[district]"] = district.strip()
        if market and market.strip() and market.lower() != "all":
            params["filters[market]"] = market.strip()

        try:
            resp = requests.get(url, params=params, timeout=Config.REQUEST_TIMEOUT)

            if resp.status_code == 401 or resp.status_code == 403:
                return {
                    "success": False,
                    "records": [],
                    "total": 0,
                    "error_message": "Invalid or expired data.gov.in API key. Falling back to local data.",
                    "source_name": "data.gov.in (Agmarknet)",
                    "source_type": "LIVE",
                }

            if resp.status_code != 200:
                return {
                    "success": False,
                    "records": [],
                    "total": 0,
                    "error_message": f"data.gov.in API returned HTTP {resp.status_code}.",
                    "source_name": "data.gov.in (Agmarknet)",
                    "source_type": "LIVE",
                }

            data = resp.json()
            raw_records = data.get("records", [])
            total = int(data.get("total", len(raw_records)))

            normalized_records: List[Dict[str, Any]] = []
            for r in raw_records:
                # Handle varying field names from Agmarknet API schemas
                crop_val = r.get("commodity") or r.get("Commodity") or crop or "Unknown"
                variety_val = r.get("variety") or r.get("Variety") or "Standard"
                state_val = r.get("state") or r.get("State") or "Tamil Nadu"
                district_val = r.get("district") or r.get("District") or "Tamil Nadu"
                market_val = r.get("market") or r.get("Market") or "General Market"

                try:
                    min_p = float(r.get("min_price") or r.get("Min_Price") or 0)
                    max_p = float(r.get("max_price") or r.get("Max_Price") or 0)
                    modal_p = float(r.get("modal_price") or r.get("Modal_Price") or min_p)
                except (ValueError, TypeError):
                    min_p, max_p, modal_p = 0.0, 0.0, 0.0

                arr_date = r.get("arrival_date") or r.get("Arrival_Date") or datetime.now().strftime("%Y-%m-%d")

                normalized_records.append({
                    "crop_name": crop_val,
                    "variety": variety_val,
                    "state": state_val,
                    "district": district_val,
                    "market_name": market_val,
                    "min_price": min_p,
                    "max_price": max_p,
                    "modal_price": modal_p,
                    "price_unit": "₹/Quintal",
                    "arrival_date": arr_date,
                    "source_name": "data.gov.in (Agmarknet)",
                    "source_type": "LIVE",
                    "external_record_id": f"GOV-{state_val}-{district_val}-{market_val}-{crop_val}-{arr_date}",
                })

            return {
                "success": True,
                "records": normalized_records,
                "total": total,
                "error_message": None,
                "source_name": "data.gov.in (Agmarknet)",
                "source_type": "LIVE",
            }

        except requests.Timeout:
            logger.warning("data.gov.in request timed out.")
            return {
                "success": False,
                "records": [],
                "total": 0,
                "error_message": "data.gov.in request timed out. Showing saved / demo data.",
                "source_name": "data.gov.in (Agmarknet)",
                "source_type": "LIVE",
            }
        except requests.RequestException as e:
            logger.error(f"data.gov.in network exception: {e}")
            return {
                "success": False,
                "records": [],
                "total": 0,
                "error_message": f"Network error contacting data.gov.in: {str(e)}",
                "source_name": "data.gov.in (Agmarknet)",
                "source_type": "LIVE",
            }


class MarketService:
    """Core market price service.

    Coordinates external provider synchronization, SQLite persistence,
    querying, comparison, and price history aggregations.
    """

    def __init__(self, provider: Optional[BaseMarketProvider] = None, db_path: Optional[str] = None):
        self.provider = provider if provider is not None else DataGovInMarketProvider()
        self.db_path = db_path

    def get_provider_status(self) -> Dict[str, Any]:
        """Return information about the active market data provider."""
        is_conf = self.provider.is_configured()
        return {
            "provider_name": "data.gov.in (Agmarknet)",
            "is_configured": is_conf,
            "mode": "LIVE" if is_conf else "DEMONSTRATION",
            "api_key_configured": is_conf,
            "status_label": "🟢 LIVE GOVERNMENT DATA" if is_conf else "🔶 DEMONSTRATION DATA (Sample)",
            "message": (
                "Connected to official data.gov.in API."
                if is_conf
                else "Running in Demonstration Mode with realistic Tamil Nadu agricultural market data. "
                     "Configure DATA_GOV_IN_API_KEY in your .env file to enable live government data."
            ),
        }

    def sync_live_data(
        self,
        crop: Optional[str] = None,
        district: Optional[str] = None,
        market: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Attempt to fetch live records from the provider and persist into SQLite."""
        if not self.provider.is_configured():
            return {
                "synced": False,
                "count": 0,
                "reason": "Provider not configured with API key.",
            }

        result = self.provider.fetch_market_prices(crop=crop, district=district, market=market, limit=100)
        if result["success"] and result["records"]:
            saved = database.save_market_prices(result["records"], db_path=self.db_path)
            return {"synced": True, "count": saved, "reason": None}
        else:
            return {"synced": False, "count": 0, "reason": result.get("error_message")}

    def query_prices(
        self,
        crop: Optional[str] = None,
        district: Optional[str] = None,
        market: Optional[str] = None,
        sort: Optional[str] = None,
        source_type: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Query prices from SQLite database with filtering, sorting, and pagination."""
        # Check if live sync should be attempted when configured
        if self.provider.is_configured() and crop:
            try:
                self.sync_live_data(crop=crop, district=district, market=market)
            except Exception as e:
                logger.warning(f"Background live sync failed: {e}")

        result = database.query_market_prices(
            crop=crop,
            district=district,
            market=market,
            sort=sort,
            source_type=source_type,
            page=page,
            limit=limit,
            db_path=self.db_path,
        )

        provider_info = self.get_provider_status()

        # Determine dominant source in current result set
        sources_present = {r["source_type"] for r in result["records"]}
        if "LIVE" in sources_present and "DEMO" not in sources_present:
            overall_source = "LIVE"
        elif "DEMO" in sources_present and "LIVE" not in sources_present:
            overall_source = "DEMO"
        elif len(sources_present) > 1:
            overall_source = "MIXED"
        else:
            overall_source = provider_info["mode"]

        return {
            "status": "success",
            "provider": provider_info,
            "overall_source_type": overall_source,
            "pagination": {
                "page": result["page"],
                "limit": result["limit"],
                "total_records": result["total_records"],
                "total_pages": result["total_pages"],
                "has_next": result["has_next"],
                "has_prev": result["has_prev"],
            },
            "records": result["records"],
        }

    def compare_markets(self, crop: str) -> Dict[str, Any]:
        """Compare commodity prices across reporting APMC markets."""
        res = database.compare_market_prices(crop=crop, db_path=self.db_path)
        provider_info = self.get_provider_status()
        res["provider"] = provider_info
        return res

    def get_price_history(self, crop: str, market: Optional[str] = None, limit: int = 30) -> Dict[str, Any]:
        """Fetch historical price observations for trends and line charts."""
        res = database.get_price_history(crop=crop, market=market, limit=limit, db_path=self.db_path)
        provider_info = self.get_provider_status()
        res["provider"] = provider_info
        return res

    def get_filter_options(self, district: Optional[str] = None) -> Dict[str, Any]:
        """Get available crops, districts, and markets for dropdown filter menus."""
        crops = database.get_available_crops(db_path=self.db_path)
        districts = database.get_available_districts(db_path=self.db_path)
        markets = database.get_available_markets(district=district, db_path=self.db_path)
        provider_info = self.get_provider_status()

        return {
            "status": "success",
            "crops": crops,
            "districts": districts,
            "markets": markets,
            "provider": provider_info,
        }
