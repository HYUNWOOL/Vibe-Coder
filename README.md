# Vibecoder Travel Recommender

FastAPI + React project for travel recommendation.

This app provides:
- City recommendation based on budget/date/continent using Amadeus flights + hotels
- Itinerary generation by style and pace (day-by-day, slot-based, alternatives per slot)

> This project does not perform booking. It only returns recommendation/planning data.

## Stack
- Backend: FastAPI, SQLAlchemy, Alembic
- Frontend: React (Vite)
- DB: MySQL (Docker Compose)
- External APIs:
  - Amadeus (flights/hotels)
  - OpenTripMap (POIs for itinerary)

## Main Features
- Search input:
  - `origin`, `continent`, `date_from`, `date_to`, `adults`, `budget_total`, `currency`
- Search output:
  - Recommended cities
  - Flight min price + hotel min price + estimated total + score
  - Offer names for flight/hotel minimum offers
  - Search summary shown on results page
- Itinerary generation:
  - Inputs: `city_code`, date range, adults, style, pace
  - Styles: `activity`, `history`, `photo`, `mixed`
  - Pace: `relaxed`, `normal`, `packed`
  - Output:
    - At least 2 variants per request (requested style + mixed/fallback variant)
    - Day-by-day plan
    - Slots per day: `morning`, `lunch`, `afternoon`, `evening`
    - 2-3 alternatives per slot
    - Each item includes:
      - `estimated_visit_minutes`
      - `estimated_travel_minutes`
      - `reasons`
- Frontend UX:
  - Itinerary section on results page
  - Date sections are collapsible to avoid long scrolling

## API Endpoints
- `POST /api/search`
  - Create city recommendations
- `GET /api/search/{search_id}`
  - Fetch cached search results
- `POST /api/itinerary`
  - Generate itinerary variants for a selected city
- `GET /health`
  - Health check
- Debug:
  - `GET /api/debug/flights`
  - `GET /api/debug/hotels`

## Data Model (New)
Alembic revision `0002_add_itinerary_tables` adds:
- `poi`
- `itinerary_request`
- `itinerary_plan`

Search tables:
- `search_request`
- `search_result`

## Environment Variables (`backend/.env`)
Required:
- `DATABASE_URL`
- `AMADEUS_API_KEY`
- `AMADEUS_API_SECRET`

Optional:
- `AMADEUS_ENV` (`test` or `production`, default `test`)
- `RESULT_CACHE_TTL_SECONDS` (default `600`)
- `CITY_CANDIDATES_LIMIT` (default `5`)
- `OPENTRIPMAP_API_KEY` (for real POI ingestion)
- `OPENTRIPMAP_BASE_URL` (default `https://api.opentripmap.com/0.1/en`)
- `HTTP_TRUST_ENV` (`true/false`, default `false`)
  - Keep `false` if OS proxy causes outbound API connection issues.

## Run (Windows)
From repo root:

```powershell
.\scripts\dev.ps1
```

Stop:

```powershell
.\scripts\stop.ps1
```

Manual:
1. Start DB
```powershell
docker compose -f infra/docker-compose.yml up -d
```
2. Backend
```powershell
python -m venv backend\.venv
.\backend\.venv\Scripts\python -m pip install -r backend\requirements.txt
.\backend\.venv\Scripts\python -m alembic -c backend\alembic.ini upgrade head
.\backend\.venv\Scripts\python -m uvicorn app.main:app --reload --app-dir backend --port 8010
```
3. Frontend
```powershell
cd frontend
npm install
npm run dev
```
![Screenshot 2026-02-01 at 14 25 06](https://github.com/user-attachments/assets/f218458a-ef51-42c3-ab37-5287fe2a9fe2)
![Screenshot 2026-02-01 at 14 24 53](https://github.com/user-attachments/assets/d4ef6e61-5965-47dd-8e49-98b9bdea841b)

## Itinerary POI Behavior
- Primary source: OpenTripMap radius API
- Parser supports both response styles documented by OpenTripMap:
  - array JSON
  - GeoJSON-like object (`features`)
- If OpenTripMap returns empty results, the backend seeds synthetic POIs per city so itinerary generation can still proceed.

## Troubleshooting
- `{"error":"amadeus_unreachable"}`:
  - Check outbound network/proxy
  - Try `HTTP_TRUST_ENV=false` and restart backend
- `No POIs returned from OpenTripMap for city ...`:
  - Verify `OPENTRIPMAP_API_KEY` validity/quota
  - Backend has synthetic POI fallback, so itinerary should still work after current updates
- `Table ... doesn't exist` on itinerary:
  - Run Alembic migration:
  ```powershell
  .\backend\.venv\Scripts\python -m alembic -c backend\alembic.ini upgrade head
  ```

## Notes
- After changing `backend/.env`, restart backend to reload settings.
- This project is for development/testing and not intended for production booking flows.
