from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import httpx

from app.core.config import settings
from functools import lru_cache

from app.integrations.http_utils import DEFAULT_TIMEOUT, request_with_retry


@dataclass(frozen=True)
class AmadeusToken:
    access_token: str
    expires_at: float


class AmadeusAuthClient:
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        env: str = "test",
        *,
        timeout: httpx.Timeout | None = None,
        max_retries: int = 2,
        backoff_base: float = 0.5,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("Amadeus API credentials are not configured.")
        self._api_key = api_key
        self._api_secret = api_secret
        self._env = env
        self._timeout = timeout or DEFAULT_TIMEOUT
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._token: AmadeusToken | None = None
        self._lock = threading.Lock()

    @property
    def base_url(self) -> str:
        return (
            "https://api.amadeus.com"
            if self._env.lower() == "production"
            else "https://test.api.amadeus.com"
        )

    def get_access_token(self) -> str:
        token = self._token
        if token and time.time() < token.expires_at - 30:
            return token.access_token

        with self._lock:
            token = self._token
            if token and time.time() < token.expires_at - 30:
                return token.access_token
            token = self._fetch_token()
            self._token = token
            return token.access_token

    def _fetch_token(self) -> AmadeusToken:
        url = f"{self.base_url}/v1/security/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self._api_key,
            "client_secret": self._api_secret,
        }
        response = request_with_retry(
            "POST",
            url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=self._timeout,
            max_retries=self._max_retries,
            backoff_base=self._backoff_base,
        )
        response.raise_for_status()
        payload = response.json()

        access_token = payload.get("access_token")
        expires_in = payload.get("expires_in", 0)
        if not access_token:
            raise RuntimeError("Amadeus token response missing access_token.")
        try:
            expires_in_value = float(expires_in)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("Amadeus token response has invalid expires_in.") from exc

        expires_at = time.time() + max(expires_in_value, 0)
        return AmadeusToken(access_token=access_token, expires_at=expires_at)


@lru_cache
def get_auth_client() -> AmadeusAuthClient:
    return AmadeusAuthClient(
        api_key=settings.amadeus_api_key,
        api_secret=settings.amadeus_api_secret,
        env=settings.amadeus_env,
    )
