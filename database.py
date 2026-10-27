"""Database module for FarmerConnect.

Handles SQLite connection, schema definition, indexing, transactions,
seeding of demonstration data, and parameterized queries.
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from config import Config


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create and return a thread-safe connection to the SQLite database.

    Configured with Row row_factory for dict-like access.
    """
    path = db_path if db_path is not None else Config.DB_PATH
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize database tables, constraints, and indexes."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        # 1. Market prices table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS market_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crop_name TEXT NOT NULL,
                variety TEXT,
                state TEXT NOT NULL,
                district TEXT NOT NULL,
                market_name TEXT NOT NULL,
                min_price REAL NOT NULL,
                max_price REAL NOT NULL,
                modal_price REAL NOT NULL,
                price_unit TEXT NOT NULL DEFAULT '₹/Quintal',
                arrival_date TEXT NOT NULL,
                source_name TEXT NOT NULL,
                source_type TEXT NOT NULL CHECK(source_type IN ('LIVE', 'DEMO')),
                fetched_at TEXT NOT NULL,
                external_record_id TEXT,
                UNIQUE(crop_name, variety, market_name, arrival_date, source_type)
            );
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_market_prices_query
            ON market_prices(crop_name, district, market_name, arrival_date);
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_market_prices_source
            ON market_prices(source_type, arrival_date DESC);
            """
        )

        # 2. Saved locations table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_name TEXT NOT NULL UNIQUE,
                district TEXT,
                state TEXT NOT NULL DEFAULT 'Tamil Nadu',
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                is_default INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )

        # 3. Price history table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crop_name TEXT NOT NULL,
                market_name TEXT NOT NULL,
                modal_price REAL NOT NULL,
                min_price REAL,
                max_price REAL,
                price_unit TEXT NOT NULL DEFAULT '₹/Quintal',
                recorded_date TEXT NOT NULL,
                source_type TEXT NOT NULL CHECK(source_type IN ('LIVE', 'DEMO')),
                created_at TEXT NOT NULL,
                UNIQUE(crop_name, market_name, recorded_date, source_type)
            );
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_price_history_crop_market
            ON price_history(crop_name, market_name, recorded_date ASC);
            """
        )

        conn.commit()


def seed_demo_data(db_path: Optional[str] = None, force: bool = False) -> int:
    """Seed realistic agricultural demonstration data for Tamil Nadu.

    Only seeds if the database is empty or if force=True.
    All seeded records are explicitly marked as source_type='DEMO' and
    source_name='FarmerConnect Seed (Demo Data)'.
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        if not force:
            cursor.execute("SELECT COUNT(*) FROM market_prices WHERE source_type = 'DEMO';")
            count = cursor.fetchone()[0]
            if count > 0:
                return 0  # Already seeded

        # Seed Locations in Tamil Nadu
        locations = [
            ("Coimbatore", "Coimbatore", "Tamil Nadu", 11.0055, 76.9661, 1),
            ("Tiruppur", "Tiruppur", "Tamil Nadu", 11.1085, 77.3411, 0),
            ("Erode", "Erode", "Tamil Nadu", 11.3410, 77.7172, 0),
            ("Salem", "Salem", "Tamil Nadu", 11.6643, 78.1460, 0),
            ("Madurai", "Madurai", "Tamil Nadu", 9.9252, 78.1198, 0),
            ("Chennai", "Chennai", "Tamil Nadu", 13.0827, 80.2707, 0),
            ("Dindigul", "Dindigul", "Tamil Nadu", 10.3673, 77.9803, 0),
            ("Thanjavur", "Thanjavur", "Tamil Nadu", 10.7870, 79.1378, 0),
            ("Pollachi", "Coimbatore", "Tamil Nadu", 10.6609, 77.0048, 0),
            ("Oddanchatram", "Dindigul", "Tamil Nadu", 10.4854, 77.7479, 0),
        ]

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for loc in locations:
            cursor.execute(
                """
                INSERT OR IGNORE INTO saved_locations
                (location_name, district, state, latitude, longitude, is_default, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (loc[0], loc[1], loc[2], loc[3], loc[4], loc[5], now_str),
            )

        # Generate realistic demo market price records
        today = datetime.now().date()
        today_str = today.strftime("%Y-%m-%d")

        # Realistic Tamil Nadu agricultural commodities & APMC markets
        demo_prices = [
            # Tomato
            ("Tomato", "Local / Hybrid", "Tamil Nadu", "Coimbatore", "Coimbatore Market", 2400, 3200, 2800, "₹/Quintal", today_str),
            ("Tomato", "Local / Hybrid", "Tamil Nadu", "Dindigul", "Oddanchatram Market", 2200, 2900, 2600, "₹/Quintal", today_str),
            ("Tomato", "Hybrid", "Tamil Nadu", "Coimbatore", "Mettupalayam Market", 2500, 3300, 2950, "₹/Quintal", today_str),
            ("Tomato", "Hybrid", "Tamil Nadu", "Chennai", "Koyambedu Wholesale", 2800, 3600, 3200, "₹/Quintal", today_str),
            ("Tomato", "Local", "Tamil Nadu", "Erode", "Erode Market", 2300, 3000, 2700, "₹/Quintal", today_str),
            ("Tomato", "Local", "Tamil Nadu", "Salem", "Salem Market", 2350, 3100, 2750, "₹/Quintal", today_str),

            # Small Onion (Shallots)
            ("Small Onion (Shallots)", "Co-5 / Sambar", "Tamil Nadu", "Coimbatore", "Coimbatore Market", 4500, 5800, 5200, "₹/Quintal", today_str),
            ("Small Onion (Shallots)", "Sambar", "Tamil Nadu", "Dindigul", "Oddanchatram Market", 4200, 5500, 4900, "₹/Quintal", today_str),
            ("Small Onion (Shallots)", "Co-5", "Tamil Nadu", "Tiruppur", "Tiruppur Market", 4600, 6000, 5300, "₹/Quintal", today_str),
            ("Small Onion (Shallots)", "Local", "Tamil Nadu", "Erode", "Perundurai Market", 4300, 5600, 5000, "₹/Quintal", today_str),
            ("Small Onion (Shallots)", "Sambar", "Tamil Nadu", "Chennai", "Koyambedu Wholesale", 4800, 6400, 5600, "₹/Quintal", today_str),

            # Big Onion (Bellary)
            ("Big Onion", "Nasik Red", "Tamil Nadu", "Coimbatore", "Coimbatore Market", 2200, 2900, 2550, "₹/Quintal", today_str),
            ("Big Onion", "Bellary Red", "Tamil Nadu", "Chennai", "Koyambedu Wholesale", 2400, 3200, 2800, "₹/Quintal", today_str),
            ("Big Onion", "Local Red", "Tamil Nadu", "Madurai", "Madurai Melur", 2100, 2800, 2450, "₹/Quintal", today_str),
            ("Big Onion", "Nasik Red", "Tamil Nadu", "Salem", "Salem Market", 2150, 2850, 2500, "₹/Quintal", today_str),

            # Paddy (Rice)
            ("Paddy (Dhan)", "Ponni", "Tamil Nadu", "Thanjavur", "Thanjavur Market", 2200, 2500, 2350, "₹/Quintal", today_str),
            ("Paddy (Dhan)", "Ponni", "Tamil Nadu", "Thanjavur", "Kumbakonam Market", 2220, 2520, 2380, "₹/Quintal", today_str),
            ("Paddy (Dhan)", "BPT / Deluxe", "Tamil Nadu", "Tiruchirappalli", "Trichy Gandhi Market", 2150, 2450, 2300, "₹/Quintal", today_str),
            ("Paddy (Dhan)", "ADT-45", "Tamil Nadu", "Madurai", "Madurai Market", 2100, 2400, 2260, "₹/Quintal", today_str),
            ("Paddy (Dhan)", "Ponni", "Tamil Nadu", "Coimbatore", "Coimbatore Market", 2250, 2580, 2420, "₹/Quintal", today_str),

            # Coconut
            ("Coconut", "Pollachi Grade-1", "Tamil Nadu", "Coimbatore", "Pollachi Market", 2600, 3200, 2900, "₹/Quintal", today_str),
            ("Coconut", "Kangeyam Copra", "Tamil Nadu", "Tiruppur", "Kangeyam Market", 2550, 3100, 2820, "₹/Quintal", today_str),
            ("Coconut", "Local Grade-1", "Tamil Nadu", "Thanjavur", "Pattukkottai Market", 2450, 2950, 2700, "₹/Quintal", today_str),
            ("Coconut", "Grade-1", "Tamil Nadu", "Chennai", "Koyambedu Wholesale", 2800, 3400, 3150, "₹/Quintal", today_str),

            # Turmeric
            ("Turmeric", "Finger (Erode Yellow)", "Tamil Nadu", "Erode", "Erode Market", 13200, 17200, 15100, "₹/Quintal", today_str),
            ("Turmeric", "Bulb", "Tamil Nadu", "Erode", "Perundurai Market", 12800, 16800, 14700, "₹/Quintal", today_str),
            ("Turmeric", "Finger", "Tamil Nadu", "Salem", "Salem Market", 12600, 16500, 14400, "₹/Quintal", today_str),

            # Banana
            ("Banana", "Nendran", "Tamil Nadu", "Coimbatore", "Coimbatore Market", 3000, 3800, 3400, "₹/Quintal", today_str),
            ("Banana", "Poovan", "Tamil Nadu", "Tiruchirappalli", "Trichy Gandhi Market", 2600, 3400, 3050, "₹/Quintal", today_str),
            ("Banana", "Robusta / Grand Naine", "Tamil Nadu", "Theni", "Cumbum Market", 2500, 3300, 2920, "₹/Quintal", today_str),
            ("Banana", "Nendran", "Tamil Nadu", "Chennai", "Koyambedu Wholesale", 3200, 4200, 3700, "₹/Quintal", today_str),

            # Cotton
            ("Cotton", "MCU-5 Long Staple", "Tamil Nadu", "Tiruppur", "Tiruppur Market", 7200, 8300, 7800, "₹/Quintal", today_str),
            ("Cotton", "DCH-32", "Tamil Nadu", "Salem", "Salem Market", 7100, 8150, 7600, "₹/Quintal", today_str),
            ("Cotton", "Bunny", "Tamil Nadu", "Madurai", "Usilampatti Market", 6950, 8000, 7450, "₹/Quintal", today_str),

            # Potato
            ("Potato", "Nilgiris Fresh", "Tamil Nadu", "Coimbatore", "Mettupalayam Market", 2300, 3100, 2700, "₹/Quintal", today_str),
            ("Potato", "Kufri Jyoti", "Tamil Nadu", "Coimbatore", "Coimbatore Market", 2400, 3200, 2850, "₹/Quintal", today_str),
            ("Potato", "Table", "Tamil Nadu", "Chennai", "Koyambedu Wholesale", 2600, 3500, 3050, "₹/Quintal", today_str),

            # Brinjal
            ("Brinjal", "Green Round", "Tamil Nadu", "Coimbatore", "Coimbatore Market", 1800, 2500, 2150, "₹/Quintal", today_str),
            ("Brinjal", "Local Purple", "Tamil Nadu", "Dindigul", "Oddanchatram Market", 1600, 2300, 1950, "₹/Quintal", today_str),
            ("Brinjal", "Green Spiny", "Tamil Nadu", "Salem", "Salem Market", 1750, 2400, 2080, "₹/Quintal", today_str),

            # Tapioca (Cassava)
            ("Tapioca", "Raw Tuber", "Tamil Nadu", "Salem", "Attur Sago Market", 1400, 1900, 1650, "₹/Quintal", today_str),
            ("Tapioca", "Raw Tuber", "Tamil Nadu", "Namakkal", "Namakkal Market", 1350, 1850, 1600, "₹/Quintal", today_str),
        ]

        inserted_count = 0
        for item in demo_prices:
            cursor.execute(
                """
                INSERT OR REPLACE INTO market_prices
                (crop_name, variety, state, district, market_name, min_price, max_price, modal_price,
                 price_unit, arrival_date, source_name, source_type, fetched_at, external_record_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'FarmerConnect Seed (Demo Data)', 'DEMO', ?, ?);
                """,
                (
                    item[0], item[1], item[2], item[3], item[4],
                    item[5], item[6], item[7], item[8], item[9],
                    now_str, f"DEMO-{item[0]}-{item[4]}-{item[9]}"
                ),
            )
            inserted_count += 1

        # Seed Price History for line charts (14 past observations for key crops)
        # Tomato, Shallots, Coconut, Turmeric, Paddy
        history_configs = [
            ("Tomato", "Coimbatore Market", 2800, 180),
            ("Tomato", "Oddanchatram Market", 2600, 160),
            ("Small Onion (Shallots)", "Coimbatore Market", 5200, 250),
            ("Small Onion (Shallots)", "Oddanchatram Market", 4900, 220),
            ("Coconut", "Pollachi Market", 2900, 80),
            ("Turmeric", "Erode Market", 15100, 450),
            ("Paddy (Dhan)", "Thanjavur Market", 2350, 40),
            ("Big Onion", "Coimbatore Market", 2550, 120),
            ("Potato", "Mettupalayam Market", 2700, 110),
            ("Banana", "Coimbatore Market", 3400, 140),
        ]

        for crop, market, current_modal, volatility in history_configs:
            for day_offset in range(14, -1, -1):
                rec_date = (today - timedelta(days=day_offset)).strftime("%Y-%m-%d")
                # Deterministic pseudo-variation based on day offset for smooth realistic trend
                variation = ((day_offset * 17) % 11 - 5) * (volatility // 4)
                modal = max(100.0, current_modal - (day_offset * (volatility // 5)) + variation)
                min_p = round(modal * 0.88, 2)
                max_p = round(modal * 1.14, 2)
                modal_p = round(modal, 2)

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO price_history
                    (crop_name, market_name, modal_price, min_price, max_price, price_unit, recorded_date, source_type, created_at)
                    VALUES (?, ?, ?, ?, ?, '₹/Quintal', ?, 'DEMO', ?);
                    """,
                    (crop, market, modal_p, min_p, max_p, rec_date, now_str),
                )

        conn.commit()
        return inserted_count


def query_market_prices(
    crop: Optional[str] = None,
    district: Optional[str] = None,
    market: Optional[str] = None,
    sort: Optional[str] = None,
    source_type: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Query market prices with filtering, sorting, and pagination."""
    page = max(1, page)
    limit = max(1, min(limit, 100))
    offset = (page - 1) * limit

    conditions: List[str] = []
    params: List[Any] = []

    if crop and crop.strip():
        conditions.append("LOWER(crop_name) LIKE ?")
        params.append(f"%{crop.strip().lower()}%")

    if district and district.strip() and district.lower() != "all":
        conditions.append("LOWER(district) = ?")
        params.append(district.strip().lower())

    if market and market.strip() and market.lower() != "all":
        conditions.append("LOWER(market_name) LIKE ?")
        params.append(f"%{market.strip().lower()}%")

    if source_type and source_type.upper() in ("LIVE", "DEMO"):
        conditions.append("source_type = ?")
        params.append(source_type.upper())

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Sort options
    sort_clauses = {
        "price_asc": "modal_price ASC",
        "price_desc": "modal_price DESC",
        "crop_asc": "crop_name ASC, modal_price ASC",
        "crop_desc": "crop_name DESC, modal_price DESC",
        "date_desc": "arrival_date DESC, modal_price DESC",
        "date_asc": "arrival_date ASC, modal_price ASC",
    }
    order_by = sort_clauses.get(sort, "arrival_date DESC, modal_price DESC")

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        # Count total matching
        count_sql = f"SELECT COUNT(*) FROM market_prices {where_clause};"
        cursor.execute(count_sql, params)
        total_records = cursor.fetchone()[0]

        # Fetch page records
        query_sql = f"""
            SELECT id, crop_name, variety, state, district, market_name,
                   min_price, max_price, modal_price, price_unit,
                   arrival_date, source_name, source_type, fetched_at, external_record_id
            FROM market_prices
            {where_clause}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?;
        """
        cursor.execute(query_sql, params + [limit, offset])
        rows = cursor.fetchall()

        total_pages = (total_records + limit - 1) // limit if total_records > 0 else 1

        records = [dict(row) for row in rows]
        return {
            "records": records,
            "total_records": total_records,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }


def get_available_crops(db_path: Optional[str] = None) -> List[str]:
    """Return distinct crop names in alphabetical order."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT crop_name FROM market_prices ORDER BY crop_name ASC;")
        return [row[0] for row in cursor.fetchall()]


def get_available_districts(db_path: Optional[str] = None) -> List[str]:
    """Return distinct district names in alphabetical order."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT district FROM market_prices ORDER BY district ASC;")
        return [row[0] for row in cursor.fetchall()]


def get_available_markets(district: Optional[str] = None, db_path: Optional[str] = None) -> List[str]:
    """Return distinct market names, optionally filtered by district."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        if district and district.lower() != "all":
            cursor.execute(
                "SELECT DISTINCT market_name FROM market_prices WHERE LOWER(district) = ? ORDER BY market_name ASC;",
                (district.lower(),),
            )
        else:
            cursor.execute("SELECT DISTINCT market_name FROM market_prices ORDER BY market_name ASC;")
        return [row[0] for row in cursor.fetchall()]


def compare_market_prices(crop: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Compare prices for a given crop across all reporting markets.

    Calculates price difference, highest price, lowest price, spread,
    and returns contextual advice.
    """
    if not crop or not crop.strip():
        return {
            "crop": "",
            "records": [],
            "highest_market": None,
            "lowest_market": None,
            "max_price_spread": 0,
            "average_modal_price": 0,
            "disclaimer": "No crop specified for comparison.",
        }

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, crop_name, variety, district, market_name, min_price, max_price,
                   modal_price, price_unit, arrival_date, source_name, source_type
            FROM market_prices
            WHERE LOWER(crop_name) LIKE ?
            ORDER BY modal_price DESC;
            """,
            (f"%{crop.strip().lower()}%",),
        )
        rows = cursor.fetchall()
        records = [dict(row) for row in rows]

        if not records:
            return {
                "crop": crop,
                "records": [],
                "highest_market": None,
                "lowest_market": None,
                "max_price_spread": 0,
                "average_modal_price": 0,
                "disclaimer": f"No market records found for '{crop}'.",
            }

        # Calculate statistics
        modal_prices = [r["modal_price"] for r in records]
        highest_record = records[0]  # sorted DESC
        lowest_record = records[-1]
        avg_modal = round(sum(modal_prices) / len(modal_prices), 2)
        price_spread = round(highest_record["modal_price"] - lowest_record["modal_price"], 2)

        # Attach difference from lowest and average to each record
        for r in records:
            r["diff_from_lowest"] = round(r["modal_price"] - lowest_record["modal_price"], 2)
            r["diff_from_avg"] = round(r["modal_price"] - avg_modal, 2)

        return {
            "crop": crop,
            "records": records,
            "total_markets": len(records),
            "highest_market": highest_record,
            "lowest_market": lowest_record,
            "max_price_spread": price_spread,
            "average_modal_price": avg_modal,
            "disclaimer": (
                "Important Note: Market comparisons reflect reported mandi prices. Actual net realization "
                "depends on transportation costs, handling charges, mandi cess, crop grading, and local demand. "
                "The highest reported price may not yield the highest net profit if transit costs exceed the price spread."
            ),
        }


def get_price_history(
    crop: str,
    market: Optional[str] = None,
    limit: int = 30,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve historical price observations for a crop and market.

    Provides chronological observations for trend analysis and chart plotting.
    """
    if not crop or not crop.strip():
        return {
            "crop": "",
            "market": market or "All Markets",
            "observations": [],
            "summary": None,
        }

    limit = max(5, min(limit, 90))
    params: List[Any] = [f"%{crop.strip().lower()}%"]
    market_filter = ""
    if market and market.strip() and market.lower() != "all":
        market_filter = "AND LOWER(market_name) LIKE ?"
        params.append(f"%{market.strip().lower()}%")

    params.append(limit)

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        query = f"""
            SELECT id, crop_name, market_name, modal_price, min_price, max_price,
                   price_unit, recorded_date, source_type
            FROM price_history
            WHERE LOWER(crop_name) LIKE ? {market_filter}
            ORDER BY recorded_date ASC
            LIMIT ?;
        """
        cursor.execute(query, params)
        rows = cursor.fetchall()
        observations = [dict(row) for row in rows]

        if not observations:
            return {
                "crop": crop,
                "market": market or "All Markets",
                "observations": [],
                "summary": None,
                "message": f"No historical records found for '{crop}'.",
            }

        modals = [o["modal_price"] for o in observations]
        first_price = modals[0]
        last_price = modals[-1]
        price_change = round(last_price - first_price, 2)
        pct_change = round(((last_price - first_price) / first_price) * 100, 1) if first_price > 0 else 0.0

        summary = {
            "min_recorded": min(modals),
            "max_recorded": max(modals),
            "avg_recorded": round(sum(modals) / len(modals), 2),
            "latest_price": last_price,
            "earliest_price": first_price,
            "price_change": price_change,
            "percentage_change": pct_change,
            "start_date": observations[0]["recorded_date"],
            "end_date": observations[-1]["recorded_date"],
            "total_points": len(observations),
            "source_type": observations[-1]["source_type"],
        }

        return {
            "crop": crop,
            "market": market or "All Markets",
            "observations": observations,
            "summary": summary,
        }


def save_market_prices(records: List[Dict[str, Any]], db_path: Optional[str] = None) -> int:
    """Save batch of market price records, avoiding duplicates.

    Updates existing records or ignores duplicates based on unique constraint.
    """
    if not records:
        return 0

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    saved_count = 0

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        for rec in records:
            crop = rec.get("crop_name", "").strip()
            variety = rec.get("variety", "Standard").strip()
            state = rec.get("state", "Tamil Nadu").strip()
            district = rec.get("district", "").strip()
            market = rec.get("market_name", "").strip()
            min_p = float(rec.get("min_price", 0))
            max_p = float(rec.get("max_price", 0))
            modal_p = float(rec.get("modal_price", 0))
            unit = rec.get("price_unit", "₹/Quintal").strip()
            date = rec.get("arrival_date", datetime.now().strftime("%Y-%m-%d")).strip()
            src_name = rec.get("source_name", "Official Data").strip()
            src_type = rec.get("source_type", "LIVE").upper()
            ext_id = rec.get("external_record_id")

            if not crop or not market:
                continue

            cursor.execute(
                """
                INSERT INTO market_prices
                (crop_name, variety, state, district, market_name, min_price, max_price, modal_price,
                 price_unit, arrival_date, source_name, source_type, fetched_at, external_record_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(crop_name, variety, market_name, arrival_date, source_type) DO UPDATE SET
                    min_price = excluded.min_price,
                    max_price = excluded.max_price,
                    modal_price = excluded.modal_price,
                    fetched_at = excluded.fetched_at;
                """,
                (crop, variety, state, district, market, min_p, max_p, modal_p, unit, date, src_name, src_type, now_str, ext_id),
            )

            # Also maintain price history point
            cursor.execute(
                """
                INSERT OR IGNORE INTO price_history
                (crop_name, market_name, modal_price, min_price, max_price, price_unit, recorded_date, source_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (crop, market, modal_p, min_p, max_p, unit, date, src_type, now_str),
            )
            saved_count += 1

        conn.commit()
    return saved_count


def get_saved_locations(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return all saved locations."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM saved_locations ORDER BY is_default DESC, location_name ASC;")
        return [dict(row) for row in cursor.fetchall()]


def get_default_location(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Return the default location or Coimbatore fallback."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM saved_locations WHERE is_default = 1 LIMIT 1;")
        row = cursor.fetchone()
        if row:
            return dict(row)
        cursor.execute("SELECT * FROM saved_locations LIMIT 1;")
        row = cursor.fetchone()
        if row:
            return dict(row)

    return {
        "location_name": Config.DEFAULT_LOCATION_NAME,
        "district": "Coimbatore",
        "state": Config.DEFAULT_STATE,
        "latitude": Config.DEFAULT_LATITUDE,
        "longitude": Config.DEFAULT_LONGITUDE,
    }


def save_location(
    location_name: str,
    latitude: float,
    longitude: float,
    district: Optional[str] = None,
    state: str = "Tamil Nadu",
    is_default: int = 0,
    db_path: Optional[str] = None,
) -> bool:
    """Save or update a location."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        if is_default == 1:
            cursor.execute("UPDATE saved_locations SET is_default = 0;")
        cursor.execute(
            """
            INSERT INTO saved_locations (location_name, district, state, latitude, longitude, is_default, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(location_name) DO UPDATE SET
                latitude = excluded.latitude,
                longitude = excluded.longitude,
                district = excluded.district,
                is_default = excluded.is_default;
            """,
            (location_name, district, state, latitude, longitude, is_default, now_str),
        )
        conn.commit()
    return True
