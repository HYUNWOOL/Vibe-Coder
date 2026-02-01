# Vibecoder — Travel Recommendation (Amadeus + FastAPI + React)

A sample, non-commercial developer project that recommends travel destinations and estimated costs based on:
- Budget
- Continent (Africa/Europe/Asia/etc)
- Date range (departure/return)
- Number of travelers

It calls Amadeus Self-Service APIs to fetch:
- Flight offers (price, duration, stops)
- Hotel offers (price estimates)

> This project does **not** book tickets/hotels. It only provides recommendations and price estimates.

---

## Architecture

- **Backend**: FastAPI (Python)
  - `/api/search` to generate recommendations (city-level)
  - Integrations: Amadeus OAuth2 + Flights + Hotels
  - DB: MySQL
  - Migrations: Alembic

- **Frontend**: React (Vite)
  - Search form
  - Results page with expandable cards

- **DB**: MySQL via Docker Compose (`infra/docker-compose.yml`)
  - Stores search requests/results for caching and reproducibility

---

## Features (MVP)

- Input: origin, continent, date range, adults, total budget
- Outputs: top destination cities
  - min flight price + top 3 flight offers
  - min hotel price + top 3 hotel offers
  - total estimate and ranking score
- Server-side caching (TTL) to reduce API calls

---

## Local Setup (Windows 11)

### One-command dev start
From repo root:

```powershell
.\scripts\dev.ps1
```

Stops everything:

```powershell
.\scripts\stop.ps1
```

### Manual setup (optional)

1) Start MySQL (Docker):

```powershell
docker compose -f infra/docker-compose.yml up -d
```

2) Backend (venv + deps + migrations + API):

```powershell
python -m venv backend\.venv
.\backend\.venv\Scripts\python -m pip install -r backend\requirements.txt
.\backend\.venv\Scripts\python -m alembic -c backend\alembic.ini upgrade head
.\backend\.venv\Scripts\python -m uvicorn app.main:app --reload --app-dir backend
```

3) Frontend (Vite dev server):

```powershell
cd frontend
npm install
npm run dev
```
![Screenshot 2026-02-01 at 14 25 06](https://github.com/user-attachments/assets/f218458a-ef51-42c3-ab37-5287fe2a9fe2)
![Screenshot 2026-02-01 at 14 24 53](https://github.com/user-attachments/assets/d4ef6e61-5965-47dd-8e49-98b9bdea841b)

