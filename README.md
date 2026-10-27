# FarmerConnect 🌾

Smart Agricultural Market Price & Weather Information System built with Flask and Python.

FarmerConnect empowers farmers and agricultural businesses with real-time crop market prices, trend analysis, multi-market price comparisons, and weather forecasts tailored for agricultural decision-making.

---

## 🚀 Features

- **Dashboard**: Overview of current market prices, top commodities, and local weather summaries.
- **Live Weather & Agro-Forecasts**: Real-time weather, temperature, humidity, wind, precipitation alerts, and farming advisories.
- **Market Price Tracker**: Live mandi/market price lookups across states, districts, and commodities.
- **Price History & Trends**: Historical trend charts and price volatility tracking.
- **Market Price Comparison**: Side-by-side comparison between neighboring markets/mandis to find optimal selling points.
- **RESTful API**: Comprehensive JSON endpoints for weather, market data, and location queries.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+, Flask
- **Database**: SQLite (built-in initialization & demo seed data)
- **Frontend**: Jinja2 Templates, Vanilla CSS & JavaScript, Chart.js
- **Testing**: Pytest

---

## 📦 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/<your-username>/FarmerConnect.git
cd FarmerConnect
```

### 2. Set Up Virtual Environment
```bash
# On Windows
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# On Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configuration (Optional)
Copy `.env.example` to `.env` and configure your API keys (e.g., OpenWeatherMap, Agmarknet) if available. The app gracefully falls back to reliable mock/demo data when API keys are not supplied.
```bash
cp .env.example .env
```

### 5. Run the Application
```bash
python app.py
```
Open your browser and navigate to: `http://localhost:5000`

---

## 🧪 Running Tests

Execute the full automated test suite with pytest:
```bash
pytest
```

---

## 📂 Project Structure

```
FarmerConnect/
├── app.py                 # Flask application entry point & routes
├── config.py              # Application settings & environment configurations
├── database.py            # SQLite schema initialization & database helpers
├── market_service.py      # Market price integration & business logic
├── weather_service.py     # Weather API client & agro-weather utilities
├── requirements.txt       # Project dependencies
├── pytest.ini             # Pytest configuration
├── templates/             # HTML templates (Jinja2)
├── static/                # CSS styles, JavaScript modules, assets
└── tests/                 # Unit & integration tests
```

---

## 📄 License
This project is open-source under the MIT License.
