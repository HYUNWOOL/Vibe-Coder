from __future__ import annotations

from functools import lru_cache
from typing import Any

import httpx

from app.core.config import settings
from app.integrations.http_utils import DEFAULT_TIMEOUT, request_with_retry


class OpenTripMapClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout: httpx.Timeout | None = None,
        max_retries: int = 2,
        backoff_base: float = 0.5,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout or DEFAULT_TIMEOUT
        self._max_retries = max_retries
        self._backoff_base = backoff_base

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    def list_pois_by_radius(
        self,
        *,
        lat: float,
        lon: float,
        radius_meters: int = 12000,
        limit: int = 180,
    ) -> list[dict[str, Any]]:
        if not self.enabled:
            return []

        params: dict[str, Any] = {
            "apikey": self._api_key,
            "lat": lat,
            "lon": lon,
            "radius": radius_meters,
            "limit": limit,
        }
        response = request_with_retry(
            "GET",
            f"{self._base_url}/places/radius",
            params=params,
            timeout=self._timeout,
            max_retries=self._max_retries,
            backoff_base=self._backoff_base,
        )
        response.raise_for_status()
        payload = response.json()
        return _extract_pois(payload)


def _extract_pois(payload: Any) -> list[dict[str, Any]]:
    # Docs indicate two response styles:
    # 1) JSON array of plain objects
    # 2) GeoJSON object with "features"
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        return []

    features = payload.get("features")
    if isinstance(features, list):
        rows: list[dict[str, Any]] = []
        for feature in features:
            if not isinstance(feature, dict):
                continue
            properties = feature.get("properties", {}) or {}
            geometry = feature.get("geometry", {}) or {}
            merged = {}
            if isinstance(properties, dict):
                merged.update(properties)
            if isinstance(geometry, dict):
                merged["geometry"] = geometry
            rows.append(merged)
        return rows

    places = payload.get("places")
    if isinstance(places, list):
        return [item for item in places if isinstance(item, dict)]

    return []


@lru_cache
def get_opentripmap_client() -> OpenTripMapClient:
    return OpenTripMapClient(
        api_key=settings.opentripmap_api_key,
        base_url=settings.opentripmap_base_url,
    )
