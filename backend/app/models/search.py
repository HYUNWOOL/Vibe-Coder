from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SearchRequest(Base):
    __tablename__ = "search_request"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="created")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    results: Mapped[list[SearchResult]] = relationship(
        back_populates="search_request", cascade="all, delete-orphan"
    )


class SearchResult(Base):
    __tablename__ = "search_result"

    id: Mapped[int] = mapped_column(primary_key=True)
    search_request_id: Mapped[int] = mapped_column(
        ForeignKey("search_request.id"), nullable=False
    )
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    search_request: Mapped[SearchRequest] = relationship(back_populates="results")
