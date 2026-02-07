"""add itinerary tables

Revision ID: 0002_add_itinerary_tables
Revises: 0001_init_search_tables
Create Date: 2026-02-06 11:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_add_itinerary_tables"
down_revision = "0001_init_search_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "poi",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("city_code", sa.String(length=3), nullable=False),
        sa.Column(
            "external_source",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'opentripmap'"),
        ),
        sa.Column("external_id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kinds", sa.Text(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("wikidata_id", sa.String(length=40), nullable=True),
        sa.Column("osm_id", sa.String(length=80), nullable=True),
        sa.Column("raw_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_poi_city_code", "poi", ["city_code"], unique=False)

    op.create_table(
        "itinerary_request",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("city_code", sa.String(length=3), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("adults", sa.Integer(), nullable=False),
        sa.Column("style", sa.String(length=20), nullable=False),
        sa.Column("pace", sa.String(length=20), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_itinerary_request_city_code",
        "itinerary_request",
        ["city_code"],
        unique=False,
    )

    op.create_table(
        "itinerary_plan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "itinerary_request_id",
            sa.Integer(),
            sa.ForeignKey("itinerary_request.id"),
            nullable=False,
        ),
        sa.Column("variant_style", sa.String(length=20), nullable=False),
        sa.Column("variant_label", sa.String(length=60), nullable=False),
        sa.Column("plan_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_itinerary_plan_itinerary_request_id",
        "itinerary_plan",
        ["itinerary_request_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_itinerary_plan_itinerary_request_id", table_name="itinerary_plan")
    op.drop_table("itinerary_plan")
    op.drop_index("ix_itinerary_request_city_code", table_name="itinerary_request")
    op.drop_table("itinerary_request")
    op.drop_index("ix_poi_city_code", table_name="poi")
    op.drop_table("poi")
