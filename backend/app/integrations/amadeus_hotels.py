from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from typing import Any

import httpx

from app.core.config import settings
from app.integrations.amadeus_auth import AmadeusAuthClient, get_auth_client
from app.integrations.http_utils import DEFAULT_TIMEOUT, request_with_retry


@dataclass(frozen=True)
class HotelOfferSummary:
    id: str | None
    name: str | None
    city_code: str | None
    currency: str | None
    price_total: float | None
    price_per_night_estimate: float | None
    rating: str | None
    address: dict[str, Any] | None
    cancellation_policy: Any | None


class AmadeusHotelsClient:
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

    def list_hotels_by_city(
        self,
        *,
        city_code: str,
        stars_min: int | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        token = self._auth_client.get_access_token()
        params: dict[str, Any] = {"cityCode": city_code}
        if stars_min is not None:
            ratings = [str(value) for value in range(stars_min, 6)]
            if len(ratings) > 4:
                ratings = ratings[:4]
            params["ratings"] = ",".join(ratings)

        response = request_with_retry(
            "GET",
            f"{self.base_url}/v1/reference-data/locations/hotels/by-city",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=self._timeout,
            max_retries=self._max_retries,
            backoff_base=self._backoff_base,
        )
        response.raise_for_status()
        payload = response.json()
        hotels = payload.get("data", [])
        if not isinstance(hotels, list):
            return []
        return hotels[:limit]

    def search_offers(
        self,
        *,
        city_code: str,
        check_in: date,
        check_out: date,
        adults: int,
        max_price: float | None = None,
        stars_min: int | None = None,
    ) -> list[HotelOfferSummary]:
        hotels = self.list_hotels_by_city(
            city_code=city_code,
            stars_min=stars_min,
        )
        if not hotels:
            return []

        hotel_ids = [hotel.get("hotelId") for hotel in hotels if hotel.get("hotelId")]
        if not hotel_ids:
            return []

        token = self._auth_client.get_access_token()
        params = {
            "hotelIds": ",".join(hotel_ids[:10]),
            "adults": adults,
            "checkInDate": check_in.isoformat(),
            "checkOutDate": check_out.isoformat(),
            "roomQuantity": 1,
        }
        response = request_with_retry(
            "GET",
            f"{self.base_url}/v3/shopping/hotel-offers",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=self._timeout,
            max_retries=self._max_retries,
            backoff_base=self._backoff_base,
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data", [])
        if not isinstance(data, list):
            return []

        hotel_lookup = {
            hotel.get("hotelId"): hotel for hotel in hotels if hotel.get("hotelId")
        }
        all_offers: list[HotelOfferSummary] = []
        nights = max((check_out - check_in).days, 0)

        for item in data:
            hotel = item.get("hotel", {}) or {}
            offers = item.get("offers", []) or []
            hotel_id = hotel.get("hotelId")
            base_hotel = hotel_lookup.get(hotel_id, {})
            name = hotel.get("name") or base_hotel.get("name")
            address = base_hotel.get("address") or hotel.get("address")
            rating = hotel.get("rating") or base_hotel.get("rating")
            city = hotel.get("cityCode") or base_hotel.get("iataCode") or city_code

            for offer in offers:
                price_total = _parse_price_total(offer)
                if max_price is not None and price_total is not None:
                    if price_total > max_price:
                        continue
                currency = _get_currency(offer)
                price_per_night = (
                    round(price_total / nights, 2)
                    if price_total is not None and nights > 0
                    else None
                )
                cancellation_policy = _get_cancellation_policy(offer)
                summary = HotelOfferSummary(
                    id=offer.get("id"),
                    name=name,
                    city_code=city,
                    currency=currency,
                    price_total=price_total,
                    price_per_night_estimate=price_per_night,
                    rating=rating,
                    address=address,
                    cancellation_policy=cancellation_policy,
                )
                all_offers.append(summary)

        all_offers.sort(key=_offer_sort_key)
        return all_offers[:3]


def _parse_price_total(offer: dict[str, Any]) -> float | None:
    price = offer.get("price", {}) or {}
    for key in ("total", "sellingTotal", "base"):
        value = price.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return None


def _get_currency(offer: dict[str, Any]) -> str | None:
    price = offer.get("price", {}) or {}
    currency = price.get("currency")
    if currency:
        return currency
    return None


def _get_cancellation_policy(offer: dict[str, Any]) -> Any | None:
    policies = offer.get("policies", {}) or {}
    return policies.get("cancellation") or offer.get("cancellation")


def _offer_sort_key(summary: HotelOfferSummary) -> tuple[float, str]:
    if summary.price_total is None:
        return (float("inf"), summary.id or "")
    return (summary.price_total, summary.id or "")


@lru_cache
def get_hotels_client() -> AmadeusHotelsClient:
    auth_client = get_auth_client()
    return AmadeusHotelsClient(auth_client, env=settings.amadeus_env)
