from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from functools import lru_cache

from app.core.config import settings
from app.integrations.amadeus_auth import AmadeusAuthClient, get_auth_client
from app.integrations.http_utils import DEFAULT_TIMEOUT, request_with_retry


class AmadeusFlightsClient:
    def __init__(
        self,
        auth_client: AmadeusAuthClient,
        env: str = "test",
        *,
        timeout: httpx.Timeout | None = None,
        max_retries: int = 2,
        backoff_base: float = 0.5,
    ) -> None:
        self._auth_client = auth_client
        self._env = env
        self._timeout = timeout or DEFAULT_TIMEOUT
        self._max_retries = max_retries
        self._backoff_base = backoff_base

    @property
    def base_url(self) -> str:
        return (
            "https://api.amadeus.com"
            if self._env.lower() == "production"
            else "https://test.api.amadeus.com"
        )

    def search_offers(
        self,
        *,
        origin: str,
        destination: str,
        date_from: date,
        date_to: date | None,
        adults: int,
        max_stops: int | None,
        currency_code: str | None = None,
    ) -> list[dict[str, Any]]:
        token = self._auth_client.get_access_token()
        params: dict[str, Any] = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": date_from.isoformat(),
            "adults": adults,
            "max": 10,
        }
        if date_to:
            params["returnDate"] = date_to.isoformat()
        if currency_code:
            params["currencyCode"] = currency_code

        response = request_with_retry(
            "GET",
            f"{self.base_url}/v2/shopping/flight-offers",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=self._timeout,
            max_retries=self._max_retries,
            backoff_base=self._backoff_base,
        )
        response.raise_for_status()
        payload = response.json()
        offers = payload.get("data", [])
        if not isinstance(offers, list):
            offers = []
        dictionaries = payload.get("dictionaries", {}) or {}
        carriers = dictionaries.get("carriers", {}) if isinstance(dictionaries, dict) else {}

        summarized: list[dict[str, Any]] = []
        for offer in offers:
            if max_stops is not None and _max_stops_for_offer(offer) > max_stops:
                continue
            summarized.append(summarize_offer(offer, carriers=carriers))
            if len(summarized) >= 3:
                break
        return summarized


def _max_stops_for_offer(offer: dict[str, Any]) -> int:
    max_stops = 0
    for itinerary in offer.get("itineraries", []) or []:
        segments = itinerary.get("segments", []) or []
        stops = max(len(segments) - 1, 0)
        if stops > max_stops:
            max_stops = stops
    return max_stops


def summarize_offer(
    offer: dict[str, Any],
    *,
    carriers: dict[str, str] | None = None,
) -> dict[str, Any]:
    price = offer.get("price", {}) or {}
    itineraries_summary = []
    for itinerary in offer.get("itineraries", []) or []:
        segments_summary = []
        for segment in itinerary.get("segments", []) or []:
            departure = segment.get("departure", {}) or {}
            arrival = segment.get("arrival", {}) or {}
            carrier_code = segment.get("carrierCode")
            segments_summary.append(
                {
                    "departure": {
                        "iata_code": departure.get("iataCode"),
                        "at": departure.get("at"),
                    },
                    "arrival": {
                        "iata_code": arrival.get("iataCode"),
                        "at": arrival.get("at"),
                    },
                    "carrier_code": carrier_code,
                    "carrier_name": (carriers or {}).get(carrier_code),
                    "flight_number": segment.get("number"),
                    "duration": segment.get("duration"),
                }
            )
        itineraries_summary.append(
            {
                "duration": itinerary.get("duration"),
                "segments": segments_summary,
            }
        )

    return {
        "id": offer.get("id"),
        "name": _build_offer_name(itineraries_summary),
        "currency": price.get("currency"),
        "price_total": price.get("grandTotal") or price.get("total"),
        "max_stops": _max_stops_for_offer(offer),
        "itineraries": itineraries_summary,
    }


def _build_offer_name(itineraries: list[dict[str, Any]]) -> str | None:
    if not itineraries:
        return None
    segments = itineraries[0].get("segments", []) or []
    if not segments:
        return None
    first_segment = segments[0]
    carrier_name = first_segment.get("carrier_name")
    carrier_code = first_segment.get("carrier_code")
    flight_number = first_segment.get("flight_number")
    if carrier_name and flight_number:
        return f"{carrier_name} {flight_number}"
    if carrier_code and flight_number:
        return f"{carrier_code}{flight_number}"
    return carrier_name or carrier_code


@lru_cache
def get_flights_client() -> AmadeusFlightsClient:
    auth_client = get_auth_client()
    return AmadeusFlightsClient(auth_client, env=settings.amadeus_env)
