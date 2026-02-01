from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.integrations.http_utils import DEFAULT_TIMEOUT, request_with_retry


OPEN_ER_API_BASE_URL = "https://open.er-api.com/v6/latest"
DEFAULT_FX_CACHE_TTL_SECONDS = 12 * 60 * 60


@dataclass
class FxCacheEntry:
    rates: dict[str, float]
    expires_at: float


class FxRatesClient:
    def __init__(
        self,
        *,
        timeout: httpx.Timeout | None = None,
        max_retries: int = 2,
        backoff_base: float = 0.5,
    ) -> None:
        self._timeout = timeout or DEFAULT_TIMEOUT
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._lock = threading.Lock()
        self._cache: dict[str, FxCacheEntry] = {}

    def get_rate(self, from_currency: str, to_currency: str) -> float | None:
        base = from_currency.upper()
        target = to_currency.upper()
        if base == target:
            return 1.0
        rates = self._get_rates(base)
        return rates.get(target)

    def _get_rates(self, base: str) -> dict[str, float]:
        now = time.time()
        cached = self._cache.get(base)
        if cached and cached.expires_at > now:
            return cached.rates

        with self._lock:
            cached = self._cache.get(base)
            if cached and cached.expires_at > now:
                return cached.rates
            rates, expires_at = self._fetch_rates(base)
            self._cache[base] = FxCacheEntry(rates=rates, expires_at=expires_at)
            return rates

    def _fetch_rates(self, base: str) -> tuple[dict[str, float], float]:
        response = request_with_retry(
            "GET",
            f"{OPEN_ER_API_BASE_URL}/{base}",
            timeout=self._timeout,
            max_retries=self._max_retries,
            backoff_base=self._backoff_base,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("result") != "success":
            raise RuntimeError(f"FX rates API error: {payload.get('error-type')}")

        rates = payload.get("rates")
        if not isinstance(rates, dict):
            raise RuntimeError("FX rates API response missing rates.")

        now = time.time()
        next_update = payload.get("time_next_update_unix")
        expires_at = now + DEFAULT_FX_CACHE_TTL_SECONDS
        if isinstance(next_update, (int, float)) and next_update > now:
            expires_at = float(next_update)

        parsed_rates: dict[str, float] = {}
        for code, value in rates.items():
            try:
                parsed_rates[code] = float(value)
            except (TypeError, ValueError):
                continue

        return parsed_rates, expires_at


_fx_client: FxRatesClient | None = None


def get_fx_client() -> FxRatesClient:
    global _fx_client
    if _fx_client is None:
        _fx_client = FxRatesClient()
    return _fx_client
