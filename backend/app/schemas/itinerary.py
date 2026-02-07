from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ItineraryStyle = Literal["activity", "history", "photo", "mixed"]
ItineraryPace = Literal["relaxed", "normal", "packed"]
ItinerarySlotName = Literal["morning", "lunch", "afternoon", "evening"]


class ItineraryRequestIn(BaseModel):
    city_code: str = Field(..., min_length=3, max_length=3)
    date_from: date
    date_to: date
    adults: int = Field(..., ge=1)
    style: ItineraryStyle
    pace: ItineraryPace = "normal"

    @field_validator("city_code", mode="before")
    @classmethod
    def _upper_city_code(cls, value: str) -> str:
        return value.upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _validate_dates(self) -> "ItineraryRequestIn":
        if self.date_to < self.date_from:
            raise ValueError("date_to must be on or after date_from.")
        return self


class SlotAlternativeOut(BaseModel):
    poi_id: int | None = None
    poi_name: str
    city_code: str
    estimated_visit_minutes: int
    estimated_travel_minutes: int
    reasons: list[str]


class DaySlotOut(BaseModel):
    slot: ItinerarySlotName
    alternatives: list[SlotAlternativeOut]


class ItineraryDayOut(BaseModel):
    day_index: int
    date: str
    slots: list[DaySlotOut]


class ItineraryVariantOut(BaseModel):
    variant_style: ItineraryStyle
    variant_label: str
    days: list[ItineraryDayOut]


class ItineraryResponse(BaseModel):
    itinerary_id: int
    city_code: str
    date_from: str
    date_to: str
    adults: int
    style: ItineraryStyle
    pace: ItineraryPace
    variants: list[ItineraryVariantOut]
