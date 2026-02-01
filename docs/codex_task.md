# Vibecoder Travel Recommender (Amadeus) — Codex Implementation Task

## Goal
Build a sample project (non-commercial, developer portfolio) that recommends destinations (city-level) based on user inputs:
- budget
- continent (Africa/Europe/Asia/etc)
- travel dates (departure/return)
- number of travelers
It should call Amadeus Self-Service APIs to fetch:
- flight offers (price, duration, stops)
- hotel offers (price per night / total estimate)
Then return ranked recommendations.

This is NOT a booking system. It only recommends and shows price estimates.

## Tech Stack
- Backend: Python + FastAPI
- Frontend: React (Vite)
- DB: MySQL (docker-compose already set up)
- Migrations: Alembic
- HTTP client: httpx
- ORM: SQLAlchemy 2.0
- Config: python-dotenv / pydantic-settings

## Repository Layout (create if missing)
backend/
  app/
    main.py
    core/
      config.py
      db.py
      logging.py
    schemas/
      search.py
    routers/
      search.py
    services/
      recommend_service.py
    integrations/
      amadeus_auth.py
      amadeus_flights.py
      amadeus_hotels.py
      amadeus_locations.py
      provider.py
    repositories/
      search_repo.py
    models/
      search.py
  alembic/
  alembic.ini
frontend/
infra/
docs/

## Environment Variables
Use backend/.env (DO NOT hardcode secrets)
- DATABASE_URL=.env.DATABASE_URL
- AMADEUS_API_KEY=.env.AMADEUS_API_KEY
- AMADEUS_API_SECRET=.env.AMADEUS_API_SECRET
- AMADEUS_ENV=test   # or production later
- RESULT_CACHE_TTL_SECONDS=600

## API Requirements (Backend)
Base path prefix: /api

### POST /api/search
Request JSON:
{
  "origin": "ICN",
  "continent": "EUROPE",
  "date_from": "2026-03-10",
  "date_to": "2026-03-17",
  "adults": 2,
  "budget_total": 2500000,
  "currency": "KRW",
  "preferences": {
    "max_stops": 1,
    "hotel_stars_min": 3,
    "free_cancellation": true
  }
}

Response JSON (immediate, synchronous MVP):
{
  "search_id": "<uuid or int>",
  "status": "done",
  "fetched_at": "<iso8601>",
  "expires_at": "<iso8601>",
  "recommendations": [
    {
      "city": "Paris",
      "city_code": "PAR",
      "country_code": "FR",
      "flight": {
        "min_total": 1200.00,
        "currency": "EUR",
        "top_offers": [ ... up to 3 ... ]
      },
      "hotel": {
        "min_total": 800.00,
        "currency": "EUR",
        "top_offers": [ ... up to 3 ... ]
      },
      "total_estimate": 2000.00,
      "score": 0.87,
      "reasons": ["within budget", "shorter duration", "good hotel value"]
    }
  ]
}

Notes:
- currency conversion is optional in MVP. If currency != API currency, return API currency and note it.
- Use caching keyed by request payload hash for TTL seconds.

### GET /api/search/{search_id}
Returns stored results from DB if available.

### GET /api/meta/continents
Returns list of supported continents and their city candidates.

## Data / City Candidates
For MVP: maintain a simple mapping in code or DB seed:
- AFRICA: [CAI, CPT, NBO, RAK]
- EUROPE: [PAR, LON, BCN, ROM, AMS, PRG]
- ASIA: [NRT, KIX, BKK, SIN, HKG, TPE]
- NORTH_AMERICA: [LAX, SFO, JFK, YVR]
- SOUTH_AMERICA: [GRU, EZE]
- OCEANIA: [SYD, MEL, AKL]

These codes are city/airport IATA codes.

## Amadeus Integration Requirements
Implement OAuth2 client_credentials token:
- POST https://test.api.amadeus.com/v1/security/oauth2/token
  grant_type=client_credentials, client_id, client_secret

Flights:
- Use Flight Offers Search (v2) or equivalent Amadeus endpoint.
- Inputs: origin, destination (city code), dates, adults, max stops preference.
- Output: keep only summary fields needed for UI + top 3 offers.

Hotels:
- Use Hotel Search / Hotel Offers endpoint available in Self-Service.
- Use city code to get hotels in city and return top 3 offers with total price estimate.

Resilience:
- rate limit/backoff: simple exponential backoff on 429/5xx
- timeouts: 10s connect/read
- structured error mapping

## DB / Migrations
Create tables:
1) search_request
- id (auto)
- request_hash (unique)
- payload_json (JSON)
- status (created/done/failed)
- created_at, updated_at

2) search_result
- id
- search_request_id (FK)
- result_json (JSON)
- fetched_at, expires_at
- created_at

Use Alembic migrations.

## Frontend Requirements (React)
Pages:
1) / : Search Form
- origin input (default ICN)
- continent select
- date range
- adults
- budget_total
- submit triggers POST /api/search and navigates to /results/:id

2) /results/:id : Results
- shows cards list
- each card shows city, total_estimate, flight min, hotel min, reasons
- expand card to show top 3 flight offers + top 3 hotel offers

Dev proxy:
- Vite proxy /api -> http://127.0.0.1:8000

## Definition of Done
- `docker compose up -d` starts MySQL
- `alembic upgrade head` creates tables
- backend runs: `python -m uvicorn app.main:app --reload`
- frontend runs: `npm run dev`
- can submit search and see ranked recommendations
- code is formatted/linted minimally, and secrets are only in .env

## Implementation Steps (Codex should follow)
1) Create backend app structure & config loader
2) Implement DB engine/session + Alembic setup + migrations
3) Implement Amadeus OAuth client + flights/hotels integration modules
4) Implement recommendation service (iterate city candidates, call providers, compute score)
5) Store search_request/result in DB with caching
6) Implement API routers and Pydantic schemas
7) Implement frontend pages + proxy + minimal UI
8) Add README run instructions and .gitignore updates
