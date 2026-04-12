# OmniChain AI Frontend

Production-style React frontend for the Smart Supply Chain Decision Intelligence System.

## What is implemented

- Sketch-driven single-page operations console
- Route input + analysis wired to `POST /get-route`
- Multi-modal comparison for road / rail / air / waterways
- Weather + disruption intelligence with scenario simulation via `POST /simulate`
- Recommendation engine with mitigation strategy and route stages
- Route map view using Leaflet
- Supply chain news + alerts panel
- Tracking section with shipment lookup, live map, timeline, and QR generation
- API status visibility for Backend / ORS / OpenWeather / Gemini

## Environment setup

Create `frontend/.env` from `.env.example`.

Required frontend variables:

- `VITE_API_BASE_URL`
- `VITE_GEMINI_API_KEY` for Gemini-powered news intelligence
- `VITE_GEMINI_MODEL` optional, defaults to `gemini-2.0-flash`

Backend keys already expected by Flask:

- `ORS_API_KEY`
- `OPENWEATHER_API_KEY`

## Install and run

```bash
npm install
npm run dev
```

Production build:

```bash
npm run build
```

## Notes

- ORS and OpenWeather status are inferred from backend response fallback flags, so the UI shows whether live APIs are being used or fallback logic is active.
- Gemini news is optional. If no Gemini key is configured, the app shows an explicit integration-needed state instead of fake news.
- Shipment tracking is Phase 2 basic implementation: it derives a trackable shipment record from the analyzed route until a live tracking backend or Supabase store is connected.
