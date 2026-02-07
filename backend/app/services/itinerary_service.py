from __future__ import annotations

import math
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.opentripmap import get_opentripmap_client
from app.models.itinerary import ItineraryPlan, ItineraryRequest, Poi
from app.schemas.itinerary import ItineraryRequestIn, ItineraryStyle

SLOT_ORDER = ("morning", "lunch", "afternoon", "evening")

CITY_CENTER_LOOKUP: dict[str, tuple[float, float]] = {
    "CAI": (30.0444, 31.2357),
    "CPT": (-33.9249, 18.4241),
    "NBO": (-1.2864, 36.8172),
    "RAK": (31.6295, -7.9811),
    "PAR": (48.8566, 2.3522),
    "LON": (51.5072, -0.1276),
    "BCN": (41.3874, 2.1686),
    "ROM": (41.9028, 12.4964),
    "AMS": (52.3676, 4.9041),
    "PRG": (50.0755, 14.4378),
    # Use city-center coordinates for metro/airport codes to avoid sparse airport-only POIs.
    "NRT": (35.6762, 139.6503),  # Tokyo
    "KIX": (34.6937, 135.5023),  # Osaka
    "BKK": (13.7563, 100.5018),
    "SIN": (1.3521, 103.8198),
    "HKG": (22.3193, 114.1694),
    "TPE": (25.0330, 121.5654),
    "LAX": (34.0522, -118.2437),
    "SFO": (37.7749, -122.4194),
    "JFK": (40.7128, -74.0060),
    "YVR": (49.2827, -123.1207),
    "GRU": (-23.5505, -46.6333),
    "EZE": (-34.6037, -58.3816),
    "SYD": (-33.8688, 151.2093),
    "MEL": (-37.8136, 144.9631),
    "AKL": (-36.8509, 174.7645),
}

STYLE_KINDS: dict[ItineraryStyle, set[str]] = {
    "activity": {
        "sport",
        "hiking",
        "amusements",
        "beaches",
        "water_parks",
        "theme_parks",
        "diving",
        "kayaking",
        "urban_environment",
        "natural",
    },
    "history": {
        "historic",
        "museums",
        "architecture",
        "archaeology",
        "religion",
        "fortifications",
        "monuments_and_memorials",
        "cultural",
    },
    "photo": {
        "view_points",
        "natural",
        "architecture",
        "bridges",
        "gardens_and_parks",
        "interesting_places",
        "panoramic",
    },
    "mixed": set(),
}
STYLE_KINDS["mixed"] = (
    STYLE_KINDS["activity"] | STYLE_KINDS["history"] | STYLE_KINDS["photo"]
)

LUNCH_KINDS = {"foods", "restaurants", "cafes"}
EVENING_KINDS = {"view_points", "architecture", "nightlife", "urban_environment"}
STYLE_LABELS = {
    "activity": "Activity Focus",
    "history": "History Focus",
    "photo": "Photo Focus",
    "mixed": "Mixed Highlights",
}
PACE_ADJUSTMENT = {"relaxed": 20, "normal": 0, "packed": -15}
PACE_SPEED_KMH = {"relaxed": 22.0, "normal": 28.0, "packed": 35.0}
SYNTHETIC_POI_TEMPLATES: list[tuple[str, str, float, float]] = [
    ("Historic Quarter Walk", "historic,architecture,cultural", 0.010, -0.008),
    ("City Museum District", "museums,historic,interesting_places", -0.006, 0.011),
    ("Riverside Viewpoint", "view_points,natural,panoramic", 0.013, 0.009),
    ("Central Food Street", "foods,restaurants,cafes,urban_environment", -0.011, -0.004),
    ("Botanical Garden", "gardens_and_parks,natural,interesting_places", 0.007, 0.014),
    ("Photography Hotspot", "view_points,architecture,interesting_places", -0.013, 0.006),
    ("Local Market Square", "foods,cultural,urban_environment", 0.004, -0.012),
    ("Urban Art Alley", "cultural,interesting_places,architecture", -0.004, 0.004),
    ("Main Cathedral", "religion,architecture,historic", 0.015, -0.001),
    ("City Park Loop", "gardens_and_parks,natural,sport", -0.009, -0.010),
    ("Night Panorama Deck", "view_points,nightlife,urban_environment", 0.012, -0.014),
    ("Activity Arena", "sport,amusements,urban_environment", -0.014, 0.013),
]


def build_itinerary(payload: ItineraryRequestIn, db: Session) -> dict[str, Any]:
    city_code = payload.city_code.upper()
    pois = _sync_city_pois(db, city_code)
    if len(pois) < 4:
        raise ValueError("Not enough POIs available for this city.")

    request_row = ItineraryRequest(
        city_code=city_code,
        date_from=payload.date_from,
        date_to=payload.date_to,
        adults=payload.adults,
        style=payload.style,
        pace=payload.pace,
        payload_json=payload.model_dump(mode="json"),
    )
    db.add(request_row)
    db.flush()

    variants: list[dict[str, Any]] = []
    for variant_style in _variant_styles(payload.style):
        days = _build_variant_days(
            pois=pois,
            date_from=payload.date_from,
            date_to=payload.date_to,
            style=variant_style,
            pace=payload.pace,
        )
        variant_payload = {
            "variant_style": variant_style,
            "variant_label": STYLE_LABELS.get(variant_style, variant_style.title()),
            "days": days,
        }
        db.add(
            ItineraryPlan(
                itinerary_request_id=request_row.id,
                variant_style=variant_style,
                variant_label=variant_payload["variant_label"],
                plan_json=variant_payload,
            )
        )
        variants.append(variant_payload)

    db.commit()
    db.refresh(request_row)

    return {
        "itinerary_id": request_row.id,
        "city_code": request_row.city_code,
        "date_from": request_row.date_from.isoformat(),
        "date_to": request_row.date_to.isoformat(),
        "adults": request_row.adults,
        "style": payload.style,
        "pace": payload.pace,
        "variants": variants,
    }


def _variant_styles(requested: ItineraryStyle) -> list[ItineraryStyle]:
    variants: list[ItineraryStyle] = [requested]
    if requested != "mixed":
        variants.append("mixed")
    else:
        variants.append("activity")
    return variants


def _sync_city_pois(db: Session, city_code: str) -> list[Poi]:
    city_code = city_code.upper()
    center = CITY_CENTER_LOOKUP.get(city_code)
    if not center:
        raise ValueError(f"Unsupported city_code for itinerary: {city_code}")

    client = get_opentripmap_client()
    if client.enabled:
        raw_items = client.list_pois_by_radius(lat=center[0], lon=center[1])
        normalized = _normalize_pois(city_code, raw_items)
        if normalized:
            _upsert_pois(db, normalized)
            db.flush()

    stored = db.execute(
        select(Poi)
        .where(Poi.city_code == city_code)
        .order_by(Poi.rating.is_(None), Poi.rating.desc())
    ).scalars().all()

    if stored:
        return stored

    # Fallback when provider is unavailable/empty so itinerary generation remains usable.
    _upsert_pois(db, _build_synthetic_pois(city_code=city_code, center=center))
    db.flush()

    fallback_rows = db.execute(
        select(Poi)
        .where(Poi.city_code == city_code)
        .order_by(Poi.rating.is_(None), Poi.rating.desc())
    ).scalars().all()
    if fallback_rows:
        return fallback_rows

    if not client.enabled:
        raise ValueError("OPENTRIPMAP_API_KEY is not configured.")
    raise ValueError(
        f"No POIs returned from OpenTripMap for city {city_code}. "
        "Check OPENTRIPMAP_API_KEY validity/quota and city coverage."
    )


def _normalize_pois(city_code: str, raw_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in raw_items:
        external_id = str(item.get("xid") or "").strip()
        name = str(item.get("name") or "").strip()
        if not external_id or not name:
            continue
        lat, lon = _extract_lat_lon(item)
        normalized.append(
            {
                "city_code": city_code,
                "external_source": "opentripmap",
                "external_id": external_id,
                "name": name,
                "kinds": item.get("kinds"),
                "lat": lat,
                "lon": lon,
                "rating": _to_float(item.get("rate")),
                "wikidata_id": item.get("wikidata"),
                "osm_id": item.get("osm"),
                "raw_json": item,
            }
        )
    return normalized


def _build_synthetic_pois(
    *,
    city_code: str,
    center: tuple[float, float],
) -> list[dict[str, Any]]:
    lat0, lon0 = center
    rows: list[dict[str, Any]] = []
    for index, (label, kinds, d_lat, d_lon) in enumerate(SYNTHETIC_POI_TEMPLATES, start=1):
        rows.append(
            {
                "city_code": city_code,
                "external_source": "synthetic",
                "external_id": f"SYNTH-{city_code}-{index}",
                "name": f"{city_code} {label}",
                "kinds": kinds,
                "lat": round(lat0 + d_lat, 6),
                "lon": round(lon0 + d_lon, 6),
                "rating": float(4 + (index % 4)),
                "wikidata_id": None,
                "osm_id": None,
                "raw_json": {
                    "synthetic": True,
                    "city_code": city_code,
                    "template": label,
                },
            }
        )
    return rows


def _extract_lat_lon(item: dict[str, Any]) -> tuple[float | None, float | None]:
    point = item.get("point", {}) or {}
    lat = _to_float(point.get("lat"))
    lon = _to_float(point.get("lon"))
    if lat is not None and lon is not None:
        return lat, lon

    geometry = item.get("geometry", {}) or {}
    if isinstance(geometry, dict):
        coordinates = geometry.get("coordinates")
        if isinstance(coordinates, (list, tuple)) and len(coordinates) >= 2:
            # GeoJSON coordinates are [lon, lat]
            lon = _to_float(coordinates[0])
            lat = _to_float(coordinates[1])
            return lat, lon
    return None, None


def _upsert_pois(db: Session, items: list[dict[str, Any]]) -> None:
    if not items:
        return
    ext_ids = [item["external_id"] for item in items]
    existing = db.execute(
        select(Poi).where(Poi.external_id.in_(ext_ids))
    ).scalars().all()
    existing_by_id = {row.external_id: row for row in existing}

    for item in items:
        row = existing_by_id.get(item["external_id"])
        if row:
            row.city_code = item["city_code"]
            row.external_source = item["external_source"]
            row.name = item["name"]
            row.kinds = item["kinds"]
            row.lat = item["lat"]
            row.lon = item["lon"]
            row.rating = item["rating"]
            row.wikidata_id = item["wikidata_id"]
            row.osm_id = item["osm_id"]
            row.raw_json = item["raw_json"]
            continue
        db.add(Poi(**item))


def _build_variant_days(
    *,
    pois: list[Poi],
    date_from: Any,
    date_to: Any,
    style: ItineraryStyle,
    pace: str,
) -> list[dict[str, Any]]:
    days_count = (date_to - date_from).days + 1
    days_count = max(days_count, 1)

    days: list[dict[str, Any]] = []
    used_primary_ids: set[int] = set()
    previous_primary: Poi | None = None

    for day_index in range(days_count):
        current_date = date_from + timedelta(days=day_index)
        slots: list[dict[str, Any]] = []

        for slot in SLOT_ORDER:
            alternatives, primary = _slot_alternatives(
                pois=pois,
                slot=slot,
                style=style,
                pace=pace,
                used_primary_ids=used_primary_ids,
                previous_primary=previous_primary,
            )
            if primary and primary.id is not None:
                used_primary_ids.add(primary.id)
                previous_primary = primary
            slots.append({"slot": slot, "alternatives": alternatives})

        days.append(
            {
                "day_index": day_index + 1,
                "date": current_date.isoformat(),
                "slots": slots,
            }
        )
    return days


def _slot_alternatives(
    *,
    pois: list[Poi],
    slot: str,
    style: ItineraryStyle,
    pace: str,
    used_primary_ids: set[int],
    previous_primary: Poi | None,
) -> tuple[list[dict[str, Any]], Poi | None]:
    ranked = sorted(
        pois,
        key=lambda poi: _poi_score(
            poi=poi,
            style=style,
            slot=slot,
            used_primary_ids=used_primary_ids,
            previous_primary=previous_primary,
        ),
        reverse=True,
    )

    alternatives: list[dict[str, Any]] = []
    selected_rows: list[Poi] = []
    selected_ids: set[int] = set()

    for poi in ranked:
        if poi.id is None or poi.id in selected_ids:
            continue
        alternatives.append(
            _build_alternative(
                poi=poi,
                slot=slot,
                style=style,
                pace=pace,
                previous_primary=previous_primary,
            )
        )
        selected_rows.append(poi)
        selected_ids.add(poi.id)
        if len(alternatives) >= 3:
            break

    if len(alternatives) < 2:
        for poi in pois:
            if poi.id is None or poi.id in selected_ids:
                continue
            alternatives.append(
                _build_alternative(
                    poi=poi,
                    slot=slot,
                    style=style,
                    pace=pace,
                    previous_primary=previous_primary,
                )
            )
            selected_rows.append(poi)
            selected_ids.add(poi.id)
            if len(alternatives) >= 2:
                break

    primary = selected_rows[0] if selected_rows else None
    return alternatives[:3], primary


def _build_alternative(
    *,
    poi: Poi,
    slot: str,
    style: ItineraryStyle,
    pace: str,
    previous_primary: Poi | None,
) -> dict[str, Any]:
    kinds = _split_kinds(poi.kinds)
    return {
        "poi_id": poi.id,
        "poi_name": poi.name,
        "city_code": poi.city_code,
        "estimated_visit_minutes": _estimate_visit_minutes(
            kinds=kinds, slot=slot, pace=pace
        ),
        "estimated_travel_minutes": _estimate_travel_minutes(
            previous=previous_primary, current=poi, pace=pace
        ),
        "reasons": _build_reasons(
            poi=poi,
            kinds=kinds,
            style=style,
            slot=slot,
            previous_primary=previous_primary,
        ),
    }


def _poi_score(
    *,
    poi: Poi,
    style: ItineraryStyle,
    slot: str,
    used_primary_ids: set[int],
    previous_primary: Poi | None,
) -> float:
    kinds = _split_kinds(poi.kinds)
    score = float(poi.rating or 0.0)

    if _matches_style(kinds, style):
        score += 4.0
    if slot == "lunch":
        score += 4.0 if _matches_any(kinds, LUNCH_KINDS) else -2.0
    if slot == "evening" and _matches_any(kinds, EVENING_KINDS):
        score += 1.5
    if poi.id in used_primary_ids:
        score -= 3.0

    distance = _distance_km(previous_primary, poi)
    if distance is not None:
        if distance <= 3:
            score += 1.5
        elif distance >= 15:
            score -= 1.0
    return score


def _estimate_visit_minutes(*, kinds: set[str], slot: str, pace: str) -> int:
    base = {"morning": 110, "lunch": 70, "afternoon": 120, "evening": 90}.get(slot, 90)

    if _matches_any(kinds, STYLE_KINDS["history"]):
        base += 20
    if _matches_any(kinds, STYLE_KINDS["activity"]):
        base += 25
    if _matches_any(kinds, STYLE_KINDS["photo"]):
        base -= 10

    total = base + PACE_ADJUSTMENT.get(pace, 0)
    return max(45, min(total, 210))


def _estimate_travel_minutes(*, previous: Poi | None, current: Poi, pace: str) -> int:
    distance = _distance_km(previous, current)
    if distance is None:
        return 20
    speed = PACE_SPEED_KMH.get(pace, 28.0)
    minutes = int(round((distance / speed) * 60)) + 10
    return max(8, min(minutes, 90))


def _build_reasons(
    *,
    poi: Poi,
    kinds: set[str],
    style: ItineraryStyle,
    slot: str,
    previous_primary: Poi | None,
) -> list[str]:
    reasons: list[str] = []
    if _matches_style(kinds, style):
        reasons.append(f"matches {style} preference")
    if slot == "lunch" and _matches_any(kinds, LUNCH_KINDS):
        reasons.append("works well for a lunch break")
    if (poi.rating or 0) >= 7:
        reasons.append("strong traveler rating")
    if _matches_any(kinds, STYLE_KINDS["history"]):
        reasons.append("historical/cultural relevance")
    if _matches_any(kinds, STYLE_KINDS["photo"]):
        reasons.append("good photo opportunities")

    distance = _distance_km(previous_primary, poi)
    if distance is not None and distance <= 3:
        reasons.append("close to previous slot")

    if not reasons:
        reasons.append("fits the selected pace")
    return reasons[:4]


def _matches_style(kinds: set[str], style: ItineraryStyle) -> bool:
    return _matches_any(kinds, STYLE_KINDS[style])


def _matches_any(kinds: set[str], targets: set[str]) -> bool:
    if not kinds:
        return False
    for kind in kinds:
        if kind in targets:
            return True
        for target in targets:
            if target in kind:
                return True
    return False


def _split_kinds(value: str | None) -> set[str]:
    if not value:
        return set()
    return {piece.strip() for piece in value.split(",") if piece.strip()}


def _distance_km(previous: Poi | None, current: Poi) -> float | None:
    if previous is None:
        return None
    if previous.lat is None or previous.lon is None:
        return None
    if current.lat is None or current.lon is None:
        return None
    return _haversine_km(previous.lat, previous.lon, current.lat, current.lon)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    d_lat = lat2_rad - lat1_rad
    d_lon = lon2_rad - lon1_rad
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(d_lon / 2) ** 2
    )
    return 2 * radius_km * math.asin(math.sqrt(a))


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
