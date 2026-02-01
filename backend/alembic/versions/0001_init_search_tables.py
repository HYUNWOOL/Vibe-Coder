"""init search tables

Revision ID: 0001_init_search_tables
Revises: 
Create Date: 2026-02-01 12:50:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_init_search_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "search_request",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'created'"),
        ),
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
        sa.UniqueConstraint("request_hash"),
    )

    op.create_table(
        "search_result",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "search_request_id",
            sa.Integer(),
            sa.ForeignKey("search_request.id"),
            nullable=False,
        ),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    op.drop_table("search_result")
    op.drop_table("search_request")
