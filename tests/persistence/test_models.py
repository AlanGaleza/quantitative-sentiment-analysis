from __future__ import annotations

from pathlib import Path

from sqlalchemy import CheckConstraint, UniqueConstraint

from quantitative_sentiment_analysis.persistence.models import Base


EXPECTED_TABLES = {
    "users",
    "sessions",
    "workspaces",
    "backtest_configs",
    "backtest_runs",
    "dataset_runs",
    "dataset_records",
    "price_candles",
}

INITIAL_MIGRATION_TABLES = EXPECTED_TABLES - {"price_candles"}


def constraint_names(table_name: str, constraint_type: type) -> set[str]:
    return {
        constraint.name or ""
        for constraint in Base.metadata.tables[table_name].constraints
        if isinstance(constraint, constraint_type)
    }


def index_names(table_name: str) -> set[str]:
    return {index.name or "" for index in Base.metadata.tables[table_name].indexes}


def test_metadata_declares_required_tables() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_workspace_and_auth_constraints_support_private_session_model() -> None:
    assert {"email", "password_hash", "disabled", "created_at"} <= set(
        Base.metadata.tables["users"].columns.keys()
    )
    assert {"token_hash", "user_id", "expires_at", "revoked_at"} <= set(
        Base.metadata.tables["sessions"].columns.keys()
    )
    assert {"slug", "owner_user_id", "name"} <= set(
        Base.metadata.tables["workspaces"].columns.keys()
    )

    assert "uq_users_email" in constraint_names("users", UniqueConstraint)
    assert "uq_sessions_token_hash" in constraint_names("sessions", UniqueConstraint)
    assert "uq_workspaces_slug" in constraint_names("workspaces", UniqueConstraint)


def test_backtest_run_tables_preserve_workspace_run_identity() -> None:
    assert "uq_backtest_runs_workspace_run_id" in constraint_names(
        "backtest_runs",
        UniqueConstraint,
    )
    assert "uq_dataset_runs_workspace_run_id" in constraint_names(
        "dataset_runs",
        UniqueConstraint,
    )
    assert "uq_dataset_records_workspace_run_record_id" in constraint_names(
        "dataset_records",
        UniqueConstraint,
    )
    assert "ix_backtest_runs_workspace_created_run" in index_names("backtest_runs")


def test_price_candle_cache_constraints_support_provider_symbol_interval_lookup() -> (
    None
):
    assert "uq_price_candles_provider_symbol_interval_open" in constraint_names(
        "price_candles",
        UniqueConstraint,
    )
    assert "ix_price_candles_lookup" in index_names("price_candles")

    names = constraint_names("price_candles", CheckConstraint)
    assert "ck_price_candles_interval_1m" in names
    assert "ck_price_candles_time_order" in names
    assert "ck_price_candles_open_price_positive" in names
    assert "ck_price_candles_high_price_bounds" in names
    assert "ck_price_candles_low_price_bounds" in names


def test_btcusd_backtest_and_dataset_record_contract_constraints_exist() -> None:
    for table_name in ("backtest_configs", "backtest_runs", "dataset_runs"):
        names = constraint_names(table_name, CheckConstraint)
        assert any(name.endswith("_btcusd") for name in names)
        assert any(name.endswith("_backtest") for name in names)

    dataset_record_constraints = constraint_names("dataset_records", CheckConstraint)
    assert "ck_dataset_records_sentiment_score_bounds" in dataset_record_constraints
    assert "ck_dataset_records_confidence_bounds" in dataset_record_constraints
    assert "ck_dataset_records_source_identity" in dataset_record_constraints
    assert "ck_dataset_records_relevance" in dataset_record_constraints
    assert "ck_dataset_records_directional_bias" in dataset_record_constraints


def test_initial_migration_mentions_every_metadata_table() -> None:
    migration = Path(
        "migrations/versions/20260616_0001_create_auth_workspace_backtest_tables.py"
    ).read_text(encoding="utf-8")

    for table_name in INITIAL_MIGRATION_TABLES:
        assert f'"{table_name}"' in migration


def test_run_history_sort_index_migration_exists() -> None:
    migration = Path(
        "migrations/versions/20260616_0002_add_backtest_run_history_sort_index.py"
    ).read_text(encoding="utf-8")

    assert "ix_backtest_runs_workspace_created_run" in migration
    assert '["workspace_id", "created_at", "run_id"]' in migration


def test_price_candle_cache_migration_exists() -> None:
    migration = Path(
        "migrations/versions/20260616_0003_create_price_candles.py"
    ).read_text(encoding="utf-8")

    assert "price_candles" in migration
    assert "uq_price_candles_provider_symbol_interval_open" in migration
    assert "ix_price_candles_lookup" in migration
