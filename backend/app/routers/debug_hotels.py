from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from httpx import HTTPStatusError, RequestError

from app.integrations.amadeus_hotels import get_hotels_client

router = APIRouter()


@router.get("/hotels")
def debug_hotels(
    city_code: str = Query(..., min_length=3, max_length=3),
    check_in: date = Query(...),
    check_out: date = Query(...),
    adults: int = Query(1, ge=1),
    max_price: float | None = Query(None, gt=0),
    stars_min: int | None = Query(None, ge=1, le=5),
) -> dict[str, Any]:
    client = get_hotels_client()
    try:
        offers = client.search_offers(
            city_code=city_code.upper(),
            check_in=check_in,
            check_out=check_out,
            adults=adults,
            max_price=max_price,
            stars_min=stars_min,
        )
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except HTTPStatusError as exc:
        status = exc.response.status_code
        detail = {
            "error": "amadeus_error",
            "status_code": status,
            "body": _safe_json(exc.response),
        }
        raise HTTPException(status_code=400 if 400 <= status < 500 else 502, detail=detail) from exc
    except RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "amadeus_unreachable",
                "message": str(exc),
                "exception_type": type(exc).__name__,
            },
        ) from exc

    return {"offers": [offer.__dict__ for offer in offers]}


def _safe_json(response: Any) -> Any:
    try:
        return response.json()
    except Exception:
        return response.text
