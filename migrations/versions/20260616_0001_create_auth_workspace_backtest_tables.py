"""create auth workspace backtest tables

Revision ID: 20260616_0001
Revises:
Create Date: 2026-06-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260616_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("disabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_sessions_token_hash"),
    )
    op.create_index("ix_sessions_token_hash", "sessions", ["token_hash"])
    op.create_index(
        "ix_sessions_user_expires_at",
        "sessions",
        ["user_id", "expires_at"],
    )

    op.create_table(
        "workspaces",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_workspaces_slug"),
    )
    op.create_index("ix_workspaces_owner_user_id", "workspaces", ["owner_user_id"])

    op.create_table(
        "backtest_configs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("instrument", sa.String(length=16), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("timeframe_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timeframe_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("instrument = 'BTCUSD'", name="ck_backtest_configs_btcusd"),
        sa.CheckConstraint("mode = 'BACKTEST'", name="ck_backtest_configs_backtest"),
        sa.CheckConstraint(
            "timeframe_end >= timeframe_start",
            name="ck_backtest_configs_timeframe_order",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "name",
            name="uq_backtest_configs_workspace_name",
        ),
    )
    op.create_index(
        "ix_backtest_configs_workspace_id",
        "backtest_configs",
        ["workspace_id"],
    )

    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("config_id", sa.Uuid(), nullable=True),
        sa.Column("instrument", sa.String(length=16), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("timeframe_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timeframe_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("instrument = 'BTCUSD'", name="ck_backtest_runs_btcusd"),
        sa.CheckConstraint("mode = 'BACKTEST'", name="ck_backtest_runs_backtest"),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'READY_FOR_DATASET')",
            name="ck_backtest_runs_status",
        ),
        sa.CheckConstraint(
            "timeframe_end >= timeframe_start",
            name="ck_backtest_runs_timeframe_order",
        ),
        sa.ForeignKeyConstraint(["config_id"], ["backtest_configs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "run_id",
            name="uq_backtest_runs_workspace_run_id",
        ),
    )
    op.create_index(
        "ix_backtest_runs_workspace_run_id",
        "backtest_runs",
        ["workspace_id", "run_id"],
    )

    op.create_table(
        "dataset_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("instrument", sa.String(length=16), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("timeframe_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timeframe_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("provider_name", sa.String(length=255), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("relevant_count", sa.Integer(), nullable=False),
        sa.Column("noise_count", sa.Integer(), nullable=False),
        sa.Column("irrelevant_count", sa.Integer(), nullable=False),
        sa.Column("model_version", sa.String(length=128), nullable=False),
        sa.Column("config_version", sa.String(length=128), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=128), nullable=False),
        sa.Column(
            "provider_limitation_provider_name",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column("provider_limitation_reason", sa.String(length=255), nullable=True),
        sa.Column("provider_limitation_detail", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("instrument = 'BTCUSD'", name="ck_dataset_runs_btcusd"),
        sa.CheckConstraint("mode = 'BACKTEST'", name="ck_dataset_runs_backtest"),
        sa.CheckConstraint(
            "status IN ('COMPLETED', 'FAILED_PROVIDER_LIMITATION')",
            name="ck_dataset_runs_terminal_status",
        ),
        sa.CheckConstraint(
            "record_count = relevant_count + noise_count + irrelevant_count",
            name="ck_dataset_runs_relevance_total",
        ),
        sa.CheckConstraint("record_count >= 0", name="ck_dataset_runs_record_count_nonnegative"),
        sa.CheckConstraint(
            "relevant_count >= 0",
            name="ck_dataset_runs_relevant_count_nonnegative",
        ),
        sa.CheckConstraint("noise_count >= 0", name="ck_dataset_runs_noise_count_nonnegative"),
        sa.CheckConstraint(
            "irrelevant_count >= 0",
            name="ck_dataset_runs_irrelevant_count_nonnegative",
        ),
        sa.CheckConstraint(
            "status != 'FAILED_PROVIDER_LIMITATION' "
            "OR provider_limitation_reason IS NOT NULL",
            name="ck_dataset_runs_limitation_reason_required",
        ),
        sa.CheckConstraint(
            "status != 'COMPLETED' OR provider_limitation_reason IS NULL",
            name="ck_dataset_runs_completed_without_limitation",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "run_id"],
            ["backtest_runs.workspace_id", "backtest_runs.run_id"],
            ondelete="CASCADE",
            name="fk_dataset_runs_backtest_run",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "run_id",
            name="uq_dataset_runs_workspace_run_id",
        ),
    )
    op.create_index(
        "ix_dataset_runs_workspace_run_id",
        "dataset_runs",
        ["workspace_id", "run_id"],
    )

    op.create_table(
        "dataset_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("record_id", sa.String(length=255), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("source_name", sa.String(length=255), nullable=True),
        sa.Column("instrument", sa.String(length=16), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("sentiment_score", sa.Float(), nullable=False),
        sa.Column("directional_bias", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("relevance", sa.String(length=16), nullable=False),
        sa.Column("model_version", sa.String(length=128), nullable=False),
        sa.Column("config_version", sa.String(length=128), nullable=False),
        sa.CheckConstraint("instrument = 'BTCUSD'", name="ck_dataset_records_btcusd"),
        sa.CheckConstraint("mode = 'BACKTEST'", name="ck_dataset_records_backtest"),
        sa.CheckConstraint(
            "directional_bias IN ('LONG', 'SHORT', 'FLAT')",
            name="ck_dataset_records_directional_bias",
        ),
        sa.CheckConstraint(
            "relevance IN ('RELEVANT', 'NOISE', 'IRRELEVANT')",
            name="ck_dataset_records_relevance",
        ),
        sa.CheckConstraint(
            "sentiment_score >= -1 AND sentiment_score <= 1",
            name="ck_dataset_records_sentiment_score_bounds",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_dataset_records_confidence_bounds",
        ),
        sa.CheckConstraint(
            "source_id IS NOT NULL OR source_name IS NOT NULL",
            name="ck_dataset_records_source_identity",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "run_id"],
            ["dataset_runs.workspace_id", "dataset_runs.run_id"],
            ondelete="CASCADE",
            name="fk_dataset_records_dataset_run",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "run_id",
            "record_id",
            name="uq_dataset_records_workspace_run_record_id",
        ),
    )
    op.create_index(
        "ix_dataset_records_workspace_run_id",
        "dataset_records",
        ["workspace_id", "run_id"],
    )
    op.create_index(
        "ix_dataset_records_export_order",
        "dataset_records",
        ["workspace_id", "run_id", "timestamp"],
    )


def downgrade() -> None:
    op.drop_index("ix_dataset_records_export_order", table_name="dataset_records")
    op.drop_index("ix_dataset_records_workspace_run_id", table_name="dataset_records")
    op.drop_table("dataset_records")
    op.drop_index("ix_dataset_runs_workspace_run_id", table_name="dataset_runs")
    op.drop_table("dataset_runs")
    op.drop_index("ix_backtest_runs_workspace_run_id", table_name="backtest_runs")
    op.drop_table("backtest_runs")
    op.drop_index("ix_backtest_configs_workspace_id", table_name="backtest_configs")
    op.drop_table("backtest_configs")
    op.drop_index("ix_workspaces_owner_user_id", table_name="workspaces")
    op.drop_table("workspaces")
    op.drop_index("ix_sessions_user_expires_at", table_name="sessions")
    op.drop_index("ix_sessions_token_hash", table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("users")
