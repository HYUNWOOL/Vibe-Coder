from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.config import settings


DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=10.0, read=10.0)


def request_with_retry(
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout | None = None,
    max_retries: int = 2,
    backoff_base: float = 0.5,
) -> httpx.Response:
    last_exc: Exception | None = None
    timeout = timeout or DEFAULT_TIMEOUT

    for attempt in range(max_retries + 1):
        try:
            with httpx.Client(timeout=timeout, trust_env=settings.http_trust_env) as client:
                response = client.request(
                    method,
                    url,
                    params=params,
                    data=data,
                    headers=headers,
                )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_exc = exc
            if attempt < max_retries:
                time.sleep(backoff_base * (2**attempt))
                continue
            raise

        if response.status_code == 429 or 500 <= response.status_code < 600:
            if attempt < max_retries:
                time.sleep(backoff_base * (2**attempt))
                continue
        return response

    if last_exc:
        raise last_exc
    raise RuntimeError("request_with_retry exhausted retries without response")
