from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from httpx import HTTPStatusError, RequestError

from app.integrations.amadeus_flights import get_flights_client

router = APIRouter()


@router.get("/flights")
def debug_flights(
    origin: str = Query(..., min_length=3, max_length=3),
    destination: str = Query(..., min_length=3, max_length=3),
    date_from: date = Query(...),
    date_to: date = Query(...),
    adults: int = Query(1, ge=1),
    max_stops: int | None = Query(None, ge=0),
) -> dict[str, Any]:
    client = get_flights_client()
    try:
        offers = client.search_offers(
            origin=origin.upper(),
            destination=destination.upper(),
            date_from=date_from,
            date_to=date_to,
            adults=adults,
            max_stops=max_stops,
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

    return {"offers": offers}


def _safe_json(response: Any) -> Any:
    try:
        return response.json()
    except Exception:
        return response.text
