"""create price candles cache

Revision ID: 20260616_0003
Revises: 20260616_0002
Create Date: 2026-06-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260616_0003"
down_revision: str | None = "20260616_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "price_candles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_name", sa.String(length=255), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("interval", sa.String(length=16), nullable=False),
        sa.Column("open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open_price", sa.Float(), nullable=False),
        sa.Column("high_price", sa.Float(), nullable=False),
        sa.Column("low_price", sa.Float(), nullable=False),
        sa.Column("close_price", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=True),
        sa.Column("quote_volume", sa.Float(), nullable=True),
        sa.Column("provider_metadata", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("interval = '1m'", name="ck_price_candles_interval_1m"),
        sa.CheckConstraint(
            "close_time > open_time",
            name="ck_price_candles_time_order",
        ),
        sa.CheckConstraint(
            "open_price > 0",
            name="ck_price_candles_open_price_positive",
        ),
        sa.CheckConstraint(
            "high_price > 0",
            name="ck_price_candles_high_price_positive",
        ),
        sa.CheckConstraint(
            "low_price > 0",
            name="ck_price_candles_low_price_positive",
        ),
        sa.CheckConstraint(
            "close_price > 0",
            name="ck_price_candles_close_price_positive",
        ),
        sa.CheckConstraint(
            "high_price >= open_price "
            "AND high_price >= low_price "
            "AND high_price >= close_price",
            name="ck_price_candles_high_price_bounds",
        ),
        sa.CheckConstraint(
            "low_price <= open_price "
            "AND low_price <= high_price "
            "AND low_price <= close_price",
            name="ck_price_candles_low_price_bounds",
        ),
        sa.CheckConstraint(
            "volume IS NULL OR volume >= 0",
            name="ck_price_candles_volume_nonnegative",
        ),
        sa.CheckConstraint(
            "quote_volume IS NULL OR quote_volume >= 0",
            name="ck_price_candles_quote_volume_nonnegative",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider_name",
            "symbol",
            "interval",
            "open_time",
            name="uq_price_candles_provider_symbol_interval_open",
        ),
    )
    op.create_index(
        "ix_price_candles_lookup",
        "price_candles",
        ["provider_name", "symbol", "interval", "open_time"],
    )


def downgrade() -> None:
    op.drop_index("ix_price_candles_lookup", table_name="price_candles")
    op.drop_table("price_candles")
