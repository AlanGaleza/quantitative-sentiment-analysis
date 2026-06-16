"""add backtest run history sort index

Revision ID: 20260616_0002
Revises: 20260616_0001
Create Date: 2026-06-16
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20260616_0002"
down_revision: str | None = "20260616_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_backtest_runs_workspace_created_run",
        "backtest_runs",
        ["workspace_id", "created_at", "run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_backtest_runs_workspace_created_run",
        table_name="backtest_runs",
    )
