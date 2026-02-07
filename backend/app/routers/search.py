from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from httpx import HTTPStatusError, RequestError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.models.search import SearchRequest, SearchResult
from app.schemas.search import SearchRequestIn, SearchResponse
from app.services.recommend_service import build_recommendations, compute_request_hash

router = APIRouter()

@router.post("/search", response_model=SearchResponse)
def create_search(
    payload: SearchRequestIn,
    db: Session = Depends(get_db),
) -> SearchResponse:
    request_hash = compute_request_hash(payload)
    search_request = db.execute(
        select(SearchRequest).where(SearchRequest.request_hash == request_hash)
    ).scalar_one_or_none()

    if search_request:
        cached = _get_latest_result(db, search_request.id)
        if cached and cached.expires_at > _now():
            return SearchResponse(
                **_with_search_input(cached.result_json, search_request.payload_json)
            )
    else:
        search_request = SearchRequest(
            request_hash=request_hash,
            payload_json=payload.model_dump(mode="json"),
            status="created",
        )
        db.add(search_request)
        db.commit()
        db.refresh(search_request)

    try:
        recommendations = build_recommendations(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
    fetched_at = _now()
    expires_at = fetched_at + timedelta(seconds=settings.result_cache_ttl_seconds)
    response_payload = {
        "search_id": search_request.id,
        "status": "done",
        "fetched_at": fetched_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "search_input": search_request.payload_json,
        "recommendations": recommendations,
    }

    result = SearchResult(
        search_request_id=search_request.id,
        result_json=response_payload,
        fetched_at=fetched_at,
        expires_at=expires_at,
    )
    search_request.status = "done"
    db.add(result)
    db.commit()

    return SearchResponse(**response_payload)


@router.get("/search/{search_id}", response_model=SearchResponse)
def get_search(search_id: int, db: Session = Depends(get_db)) -> SearchResponse:
    search_request = db.get(SearchRequest, search_id)
    if not search_request:
        raise HTTPException(status_code=404, detail="search_id not found")

    latest = _get_latest_result(db, search_request.id)
    if not latest:
        raise HTTPException(status_code=404, detail="search result not found")
    return SearchResponse(
        **_with_search_input(latest.result_json, search_request.payload_json)
    )


def _get_latest_result(db: Session, search_request_id: int) -> SearchResult | None:
    return db.execute(
        select(SearchResult)
        .where(SearchResult.search_request_id == search_request_id)
        .order_by(SearchResult.fetched_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _safe_json(response: object) -> object:
    try:
        return response.json()  # type: ignore[attr-defined]
    except Exception:
        return str(response)


def _with_search_input(result_json: dict, search_payload: dict) -> dict:
    payload = dict(result_json)
    payload["search_input"] = search_payload
    return payload
