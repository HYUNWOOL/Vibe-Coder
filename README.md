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

### 1) Start MySQL (Docker)
From repo root:

```powershell
docker compose -f infra/docker-compose.yml up -d
docker ps
