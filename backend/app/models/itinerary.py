from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Poi(Base):
    __tablename__ = "poi"

    id: Mapped[int] = mapped_column(primary_key=True)
    city_code: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    external_source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="opentripmap"
    )
    external_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kinds: Mapped[str] = mapped_column(Text, nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=True)
    lon: Mapped[float] = mapped_column(Float, nullable=True)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    wikidata_id: Mapped[str] = mapped_column(String(40), nullable=True)
    osm_id: Mapped[str] = mapped_column(String(80), nullable=True)
    raw_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ItineraryRequest(Base):
    __tablename__ = "itinerary_request"

    id: Mapped[int] = mapped_column(primary_key=True)
    city_code: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    adults: Mapped[int] = mapped_column(Integer, nullable=False)
    style: Mapped[str] = mapped_column(String(20), nullable=False)
    pace: Mapped[str] = mapped_column(String(20), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    plans: Mapped[list["ItineraryPlan"]] = relationship(
        back_populates="itinerary_request",
        cascade="all, delete-orphan",
    )


class ItineraryPlan(Base):
    __tablename__ = "itinerary_plan"

    id: Mapped[int] = mapped_column(primary_key=True)
    itinerary_request_id: Mapped[int] = mapped_column(
        ForeignKey("itinerary_request.id"), nullable=False, index=True
    )
    variant_style: Mapped[str] = mapped_column(String(20), nullable=False)
    variant_label: Mapped[str] = mapped_column(String(60), nullable=False)
    plan_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    itinerary_request: Mapped["ItineraryRequest"] = relationship(back_populates="plans")
