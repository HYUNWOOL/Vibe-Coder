from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import date
from typing import Any

from app.core.config import settings
from app.integrations.amadeus_flights import get_flights_client
from app.integrations.amadeus_hotels import HotelOfferSummary, get_hotels_client
from app.integrations.fx_rates import FxRatesClient, get_fx_client
from app.schemas.search import SearchRequestIn


CityCandidate = dict[str, str]

CONTINENT_CANDIDATES: dict[str, list[CityCandidate]] = {
    "AFRICA": [
        {"city": "Cairo", "city_code": "CAI", "country_code": "EG"},
        {"city": "Cape Town", "city_code": "CPT", "country_code": "ZA"},
        {"city": "Nairobi", "city_code": "NBO", "country_code": "KE"},
        {"city": "Marrakesh", "city_code": "RAK", "country_code": "MA"},
    ],
    "EUROPE": [
        {"city": "Paris", "city_code": "PAR", "country_code": "FR"},
        {"city": "London", "city_code": "LON", "country_code": "GB"},
        {"city": "Barcelona", "city_code": "BCN", "country_code": "ES"},
        {"city": "Rome", "city_code": "ROM", "country_code": "IT"},
        {"city": "Amsterdam", "city_code": "AMS", "country_code": "NL"},
        {"city": "Prague", "city_code": "PRG", "country_code": "CZ"},
    ],
    "ASIA": [
        {"city": "Tokyo", "city_code": "NRT", "country_code": "JP"},
        {"city": "Osaka", "city_code": "KIX", "country_code": "JP"},
        {"city": "Bangkok", "city_code": "BKK", "country_code": "TH"},
        {"city": "Singapore", "city_code": "SIN", "country_code": "SG"},
        {"city": "Hong Kong", "city_code": "HKG", "country_code": "HK"},
        {"city": "Taipei", "city_code": "TPE", "country_code": "TW"},
    ],
    "NORTH_AMERICA": [
        {"city": "Los Angeles", "city_code": "LAX", "country_code": "US"},
        {"city": "San Francisco", "city_code": "SFO", "country_code": "US"},
        {"city": "New York", "city_code": "JFK", "country_code": "US"},
        {"city": "Vancouver", "city_code": "YVR", "country_code": "CA"},
    ],
    "SOUTH_AMERICA": [
        {"city": "Sao Paulo", "city_code": "GRU", "country_code": "BR"},
        {"city": "Buenos Aires", "city_code": "EZE", "country_code": "AR"},
    ],
    "OCEANIA": [
        {"city": "Sydney", "city_code": "SYD", "country_code": "AU"},
        {"city": "Melbourne", "city_code": "MEL", "country_code": "AU"},
        {"city": "Auckland", "city_code": "AKL", "country_code": "NZ"},
    ],
}


def compute_request_hash(request: SearchRequestIn) -> str:
    payload = request.model_dump(mode="json")
    packed = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(packed.encode("utf-8")).hexdigest()


def get_city_candidates(continent: str) -> list[CityCandidate]:
    cities = CONTINENT_CANDIDATES.get(continent.upper())
    if not cities:
        raise ValueError(f"Unsupported continent: {continent}")
    limit = min(max(settings.city_candidates_limit, 1), 5)
    return cities[:limit]


def build_recommendations(request: SearchRequestIn) -> list[dict[str, Any]]:
    flights_client = get_flights_client()
    hotels_client = get_hotels_client()
    fx_client = get_fx_client()
    candidates = get_city_candidates(request.continent)

    recommendations: list[dict[str, Any]] = []
    for candidate in candidates:
        city_code = candidate["city_code"]
        flight_offers = flights_client.search_offers(
            origin=request.origin,
            destination=city_code,
            date_from=request.date_from,
            date_to=request.date_to,
            adults=request.adults,
            max_stops=_pref_max_stops(request),
            currency_code=request.currency,
        )
        flight_offers = _convert_flight_offers(
            flight_offers,
            target_currency=request.currency,
            fx_client=fx_client,
        )

        hotel_offers = hotels_client.search_offers(
            city_code=city_code,
            check_in=_to_date(request.date_from),
            check_out=_to_date(request.date_to),
            adults=request.adults,
            max_price=None,
            stars_min=_pref_hotel_stars(request),
            currency_code=request.currency,
        )
        hotel_offers = _convert_hotel_offers(
            hotel_offers,
            target_currency=request.currency,
            fx_client=fx_client,
        )

        flight_min_total, flight_currency, flight_min_offer_name = _min_flight_total(
            flight_offers
        )
        hotel_min_total, hotel_currency, hotel_min_offer_name = _min_hotel_total(
            hotel_offers
        )
        total_estimate, total_currency = _combine_totals(
            flight_min_total,
            flight_currency,
            hotel_min_total,
            hotel_currency,
        )
        reasons = _build_reasons(
            request=request,
            total_estimate=total_estimate,
            total_currency=total_currency,
            flight_currency=flight_currency,
            hotel_currency=hotel_currency,
            flight_offers=flight_offers,
        )

        recommendations.append(
            {
                "city": candidate["city"],
                "city_code": city_code,
                "country_code": candidate["country_code"],
                "flight": {
                    "min_total": flight_min_total,
                    "currency": flight_currency,
                    "min_offer_name": flight_min_offer_name,
                    "top_offers": flight_offers,
                },
                "hotel": {
                    "min_total": hotel_min_total,
                    "currency": hotel_currency,
                    "min_offer_name": hotel_min_offer_name,
                    "top_offers": [asdict(offer) for offer in hotel_offers],
                },
                "total_estimate": total_estimate,
                "score": 0.0,
                "reasons": reasons,
            }
        )

    _apply_scores(recommendations)
    return recommendations


def _to_date(value: date) -> date:
    return value


def _convert_flight_offers(
    offers: list[dict[str, Any]],
    *,
    target_currency: str,
    fx_client: FxRatesClient,
) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    for offer in offers:
        currency = offer.get("currency")
        amount = _parse_money(offer.get("price_total"))
        if not currency or amount is None:
            continue
        rate = fx_client.get_rate(currency, target_currency)
        if rate is None:
            continue
        converted_offer = dict(offer)
        converted_offer["currency"] = target_currency
        converted_offer["price_total"] = round(amount * rate, 2)
        converted.append(converted_offer)
    return converted


def _convert_hotel_offers(
    offers: list[HotelOfferSummary],
    *,
    target_currency: str,
    fx_client: FxRatesClient,
) -> list[HotelOfferSummary]:
    converted: list[HotelOfferSummary] = []
    for offer in offers:
        if not offer.currency or offer.price_total is None:
            continue
        rate = fx_client.get_rate(offer.currency, target_currency)
        if rate is None:
            continue
        price_total = round(offer.price_total * rate, 2)
        price_per_night = (
            round(offer.price_per_night_estimate * rate, 2)
            if offer.price_per_night_estimate is not None
            else None
        )
        converted.append(
            HotelOfferSummary(
                id=offer.id,
                name=offer.name,
                city_code=offer.city_code,
                currency=target_currency,
                price_total=price_total,
                price_per_night_estimate=price_per_night,
                rating=offer.rating,
                address=offer.address,
                cancellation_policy=offer.cancellation_policy,
            )
        )
    return converted


def _pref_max_stops(request: SearchRequestIn) -> int | None:
    if request.preferences:
        return request.preferences.max_stops
    return None


def _pref_hotel_stars(request: SearchRequestIn) -> int | None:
    if request.preferences:
        return request.preferences.hotel_stars_min
    return None


def _min_flight_total(
    offers: list[dict[str, Any]],
) -> tuple[float | None, str | None, str | None]:
    min_total: float | None = None
    currency: str | None = None
    offer_name: str | None = None
    for offer in offers:
        value = offer.get("price_total")
        parsed = _parse_money(value)
        if parsed is None:
            continue
        if min_total is None or parsed < min_total:
            min_total = parsed
            currency = offer.get("currency")
            offer_name = offer.get("name")
    return min_total, currency, offer_name


def _min_hotel_total(
    offers: list[HotelOfferSummary],
) -> tuple[float | None, str | None, str | None]:
    min_total: float | None = None
    currency: str | None = None
    offer_name: str | None = None
    for offer in offers:
        if offer.price_total is None:
            continue
        if min_total is None or offer.price_total < min_total:
            min_total = offer.price_total
            currency = offer.currency
            offer_name = offer.name
    return min_total, currency, offer_name


def _combine_totals(
    flight_total: float | None,
    flight_currency: str | None,
    hotel_total: float | None,
    hotel_currency: str | None,
) -> tuple[float | None, str | None]:
    if (
        flight_total is None
        or hotel_total is None
        or not flight_currency
        or not hotel_currency
    ):
        return None, None
    if flight_currency != hotel_currency:
        return None, None
    return round(flight_total + hotel_total, 2), flight_currency


def _apply_scores(recommendations: list[dict[str, Any]]) -> None:
    totals = [
        rec["total_estimate"]
        for rec in recommendations
        if rec.get("total_estimate") is not None
    ]
    if not totals:
        for rec in recommendations:
            rec["score"] = 0.0
        return

    min_total = min(totals)
    max_total = max(totals)
    for rec in recommendations:
        total = rec.get("total_estimate")
        if total is None:
            rec["score"] = 0.0
            continue
        if max_total == min_total:
            rec["score"] = 1.0
            continue
        score = 1 - (total - min_total) / (max_total - min_total)
        rec["score"] = round(score, 3)


def _build_reasons(
    *,
    request: SearchRequestIn,
    total_estimate: float | None,
    total_currency: str | None,
    flight_currency: str | None,
    hotel_currency: str | None,
    flight_offers: list[dict[str, Any]],
) -> list[str]:
    reasons: list[str] = []
    if flight_currency and flight_currency != request.currency:
        reasons.append("flight currency differs from request")
    if hotel_currency and hotel_currency != request.currency:
        reasons.append("hotel currency differs from request")
    if total_estimate is not None and total_currency is not None:
        if total_estimate <= request.budget_total:
            reasons.append("within budget")
    min_stops = _min_stops(flight_offers)
    if min_stops is not None and min_stops <= 1:
        reasons.append("fewer stops")
    if not reasons:
        reasons.append("estimated total based on available offers")
    return reasons


def _min_stops(offers: list[dict[str, Any]]) -> int | None:
    stops = [offer.get("max_stops") for offer in offers if offer.get("max_stops") is not None]
    if not stops:
        return None
    return min(stops)


def _parse_money(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
