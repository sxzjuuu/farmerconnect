"""FarmerConnect - Smart Agricultural Market Price and Weather Information System.

Flask application entrypoint with modular page routes, RESTful JSON APIs,
error handlers, and database lifecycle management.
"""

import os
import logging
from typing import Any, Dict
from flask import Flask, jsonify, render_template, request

from config import Config
import database
from weather_service import get_weather_forecast, search_locations, validate_coordinates
from market_service import MarketService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("farmerconnect")


def create_app(config_class=Config) -> Flask:
    """Application factory for FarmerConnect."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize market service
    market_service = MarketService(db_path=app.config.get("DB_PATH"))

    # Ensure database is initialized and seeded with demo data
    with app.app_context():
        try:
            database.init_db(app.config.get("DB_PATH"))
            database.seed_demo_data(app.config.get("DB_PATH"))
            logger.info("Database initialized and demo data verified.")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")

    # =========================================================================
    # Template Context Processors & Helpers
    # =========================================================================
    @app.context_processor
    def inject_global_data():
        """Inject default location and app metadata into all templates."""
        default_loc = database.get_default_location(app.config.get("DB_PATH"))
        provider_status = market_service.get_provider_status()
        return {
            "app_title": "FarmerConnect",
            "app_subtitle": "Smart Agricultural Market Price & Weather Information System",
            "default_location": default_loc,
            "provider_status": provider_status,
        }

    # =========================================================================
    # Page Routes
    # =========================================================================
    @app.route("/")
    def index():
        """Home Dashboard view."""
        return render_template("index.html", active_page="dashboard")

    @app.route("/weather")
    def weather():
        """Live Weather details and agricultural forecast view."""
        return render_template("weather.html", active_page="weather")

    @app.route("/markets")
    def markets():
        """Agricultural Market Prices search and filtering view."""
        return render_template("markets.html", active_page="markets")

    @app.route("/compare")
    def compare():
        """Mandi Market Price Comparison view."""
        return render_template("compare.html", active_page="compare")

    @app.route("/history")
    def history():
        """Price History trend analysis view."""
        return render_template("history.html", active_page="history")

    @app.route("/about")
    def about():
        """About the Project and Academic Documentation view."""
        return render_template("about.html", active_page="about")

    # =========================================================================
    # API Routes
    # =========================================================================
    @app.route("/api/health", methods=["GET"])
    def api_health():
        """Health check endpoint for monitoring application status."""
        return jsonify({
            "status": "healthy",
            "service": "FarmerConnect",
            "version": "1.0.0",
            "database": "connected",
            "provider_mode": market_service.get_provider_status()["mode"],
        }), 200

    @app.route("/api/locations", methods=["GET"])
    def api_locations():
        """Search locations by name (Tamil Nadu focus)."""
        query = request.args.get("q", "").strip()
        if not query:
            # Return saved locations if query is empty
            saved = database.get_saved_locations(app.config.get("DB_PATH"))
            return jsonify({
                "status": "success",
                "count": len(saved),
                "locations": saved,
            }), 200

        results = search_locations(query)
        return jsonify({
            "status": "success",
            "query": query,
            "count": len(results),
            "locations": results,
        }), 200

    @app.route("/api/weather", methods=["GET"])
    def api_weather():
        """Retrieve live weather and 5-day forecast.

        Accepts either 'lat' and 'lon', or 'location' name.
        """
        lat_arg = request.args.get("lat")
        lon_arg = request.args.get("lon")
        loc_arg = request.args.get("location")
        force_refresh = request.args.get("refresh", "0") in ("1", "true", "True")

        lat = None
        lon = None
        loc_name = loc_arg

        if lat_arg is not None and lon_arg is not None:
            valid, err = validate_coordinates(lat_arg, lon_arg)
            if not valid:
                return jsonify({"status": "error", "message": err}), 400
            lat = float(lat_arg)
            lon = float(lon_arg)
        elif loc_arg:
            matches = search_locations(loc_arg)
            if matches:
                lat = matches[0]["latitude"]
                lon = matches[0]["longitude"]
                loc_name = matches[0]["name"]
            else:
                return jsonify({
                    "status": "error",
                    "message": f"Location '{loc_arg}' could not be resolved. Please try selecting a nearby Tamil Nadu district.",
                }), 404
        else:
            # Fall back to default location
            def_loc = database.get_default_location(app.config.get("DB_PATH"))
            lat = def_loc["latitude"]
            lon = def_loc["longitude"]
            loc_name = def_loc["location_name"]

        result = get_weather_forecast(lat, lon, location_name=loc_name, force_refresh=force_refresh)
        status_code = 200 if result.get("status") == "success" else 502
        return jsonify(result), status_code

    @app.route("/api/markets", methods=["GET"])
    def api_markets():
        """Retrieve agricultural market prices with filtering, sorting, and pagination."""
        crop = request.args.get("crop")
        district = request.args.get("district")
        market = request.args.get("market")
        sort = request.args.get("sort")
        source_type = request.args.get("source_type")

        try:
            page = int(request.args.get("page", 1))
        except ValueError:
            page = 1

        try:
            limit = int(request.args.get("limit", 20))
        except ValueError:
            limit = 20

        result = market_service.query_prices(
            crop=crop,
            district=district,
            market=market,
            sort=sort,
            source_type=source_type,
            page=page,
            limit=limit,
        )
        return jsonify(result), 200

    @app.route("/api/markets/filters", methods=["GET"])
    def api_market_filters():
        """Retrieve available filter dropdown values (crops, districts, markets)."""
        district = request.args.get("district")
        result = market_service.get_filter_options(district=district)
        return jsonify(result), 200

    @app.route("/api/markets/compare", methods=["GET"])
    def api_market_compare():
        """Compare prices for a given commodity across multiple markets."""
        crop = request.args.get("crop", "").strip()
        if not crop:
            # Pick the top crop by default
            available = database.get_available_crops(app.config.get("DB_PATH"))
            crop = available[0] if available else "Tomato"

        result = market_service.compare_markets(crop=crop)
        return jsonify(result), 200

    @app.route("/api/markets/history", methods=["GET"])
    def api_market_history():
        """Retrieve price history for a given commodity and market."""
        crop = request.args.get("crop", "").strip()
        market = request.args.get("market")

        try:
            limit = int(request.args.get("limit", 30))
        except ValueError:
            limit = 30

        if not crop:
            available = database.get_available_crops(app.config.get("DB_PATH"))
            crop = available[0] if available else "Tomato"

        result = market_service.get_price_history(crop=crop, market=market, limit=limit)
        return jsonify(result), 200

    @app.route("/api/locations/select", methods=["POST"])
    def api_select_location():
        """Set or save the active/default location."""
        data = request.get_json() or {}
        name = data.get("location_name")
        lat = data.get("latitude")
        lon = data.get("longitude")
        district = data.get("district")

        if not name or lat is None or lon is None:
            return jsonify({"status": "error", "message": "Missing required fields (location_name, latitude, longitude)."}), 400

        valid, err = validate_coordinates(lat, lon)
        if not valid:
            return jsonify({"status": "error", "message": err}), 400

        database.save_location(
            location_name=name,
            latitude=float(lat),
            longitude=float(lon),
            district=district,
            is_default=1,
            db_path=app.config.get("DB_PATH"),
        )

        return jsonify({
            "status": "success",
            "message": f"Default location updated to {name}.",
            "location": {
                "location_name": name,
                "latitude": float(lat),
                "longitude": float(lon),
                "district": district,
            },
        }), 200

    # =========================================================================
    # Error Handlers
    # =========================================================================
    @app.errorhandler(404)
    def handle_not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"status": "error", "message": "API endpoint not found."}), 404
        return render_template("base.html", error_title="Page Not Found (404)", error_message="The requested page could not be located."), 404

    @app.errorhandler(500)
    def handle_server_error(e):
        logger.error(f"Internal server error: {e}")
        if request.path.startswith("/api/"):
            return jsonify({"status": "error", "message": "An internal server error occurred."}), 500
        return render_template("base.html", error_title="Server Error (500)", error_message="An internal server error occurred. Please try again later."), 500

    return app


# Create default instance for WSGI runners
app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "1") in ("1", "true", "True")
    print(f"\n========================================================")
    print(f"  FarmerConnect Application Starting on Windows")
    print(f"  URL: http://127.0.0.1:{port}")
    print(f"  Mode: {'Debug' if debug else 'Production'}")
    print(f"========================================================\n")
    app.run(host="127.0.0.1", port=port, debug=debug)
