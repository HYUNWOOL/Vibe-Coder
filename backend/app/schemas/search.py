from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class SearchPreferences(BaseModel):
    max_stops: int | None = Field(None, ge=0)
    hotel_stars_min: int | None = Field(None, ge=1, le=5)
    free_cancellation: bool | None = None


class SearchRequestIn(BaseModel):
    origin: str = Field(..., min_length=3, max_length=3)
    continent: str
    date_from: date
    date_to: date
    adults: int = Field(..., ge=1)
    budget_total: float = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
    preferences: SearchPreferences | None = None

    @field_validator("origin", "currency", mode="before")
    @classmethod
    def _upper_codes(cls, value: str) -> str:
        return value.upper() if isinstance(value, str) else value

    @field_validator("continent", mode="before")
    @classmethod
    def _upper_continent(cls, value: str) -> str:
        return value.upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _validate_dates(self) -> "SearchRequestIn":
        if self.date_to < self.date_from:
            raise ValueError("date_to must be on or after date_from.")
        return self


class SearchResponse(BaseModel):
    search_id: int
    status: str
    fetched_at: str
    expires_at: str
    search_input: dict[str, Any] | None = None
    recommendations: list[dict[str, Any]]
