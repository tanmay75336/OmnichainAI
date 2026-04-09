# Smart Supply Chain Optimization Backend

Production-ready Flask backend for route intelligence, supply chain risk scoring, disruption simulation, and prompt-ready AI insights.

## Features

- Modular Flask architecture with app factory
- Google Maps Distance Matrix integration
- OpenWeather integration
- Weighted route risk scoring
- Static regional risk metadata for Tier-2, Tier-3, and SEZ zones
- What-if simulation engine for disruptions
- Multi-modal transport support: road, rail, air, waterways
- In-memory TTL caching
- Centralized logging and error handling
- LLM prompt preparation for downstream AI insights

## Run

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

## Environment Files

The backend checks for environment values in this order:

1. `backend/.env`
2. repo root `.env`

You can keep your existing root `.env`, or add a backend-specific one later.

## API

### `GET /`

Service overview and available endpoints.

### `GET /health`

Health check endpoint.

### `POST /get-route`

```json
{
  "source": "Mumbai",
  "destination": "Pune",
  "transport_mode": "road",
  "region_type": "tier_2"
}
```

### `POST /simulate`

```json
{
  "route": {
    "source": "Mumbai",
    "destination": "Pune",
    "transport_mode": "road",
    "region_type": "tier_2"
  },
  "disruption_type": "monsoon"
}
```
