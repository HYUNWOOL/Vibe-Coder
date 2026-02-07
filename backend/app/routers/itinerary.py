from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from httpx import HTTPStatusError, RequestError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.itinerary import ItineraryRequestIn, ItineraryResponse
from app.services.itinerary_service import build_itinerary

router = APIRouter()


@router.post("/itinerary", response_model=ItineraryResponse)
def create_itinerary(
    payload: ItineraryRequestIn,
    db: Session = Depends(get_db),
) -> ItineraryResponse:
    try:
        result = build_itinerary(payload, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPStatusError as exc:
        status = exc.response.status_code
        detail = {
            "error": "poi_provider_error",
            "status_code": status,
            "body": _safe_json(exc.response),
        }
        raise HTTPException(status_code=400 if 400 <= status < 500 else 502, detail=detail) from exc
    except RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "poi_provider_unreachable",
                "message": str(exc),
                "exception_type": type(exc).__name__,
            },
        ) from exc

    return ItineraryResponse(**result)


def _safe_json(response: object) -> object:
    try:
        return response.json()  # type: ignore[attr-defined]
    except Exception:
        return str(response)
