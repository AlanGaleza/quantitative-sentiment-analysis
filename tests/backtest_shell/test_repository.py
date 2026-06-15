from __future__ import annotations

from datetime import UTC, datetime

import pytest

from quantitative_sentiment_analysis.backtest_shell import (
    BacktestShellRunNotFoundError,
    CreateBacktestRunRequest,
    InMemoryBacktestShellRepository,
)
from quantitative_sentiment_analysis.contracts import Instrument, RunMode


TIMEFRAME_START = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
TIMEFRAME_END = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
CREATED_AT = datetime(2026, 6, 8, 12, 30, tzinfo=UTC)


def make_request() -> CreateBacktestRunRequest:
    return CreateBacktestRunRequest(
        timeframe_start=TIMEFRAME_START,
        timeframe_end=TIMEFRAME_END,
    )


def test_repository_creates_draft_run_with_injected_id_and_clock() -> None:
    repository = InMemoryBacktestShellRepository(
        run_id_factory=lambda workspace_id, request: "draft-run-fixed",
        clock=lambda: CREATED_AT,
    )

    run = repository.create_draft_run("workspace-alpha", make_request())

    assert run.workspace_id == "workspace-alpha"
    assert run.run_id == "draft-run-fixed"
    assert run.instrument is Instrument.BTCUSD
    assert run.mode is RunMode.BACKTEST
    assert run.created_at == CREATED_AT
    assert run.quality_report_path == (
        "/workspaces/workspace-alpha/backtests/draft-run-fixed/quality"
    )
    assert repository.get_run("workspace-alpha", "draft-run-fixed") == run


def test_repository_default_run_ids_are_url_safe_and_sequential() -> None:
    repository = InMemoryBacktestShellRepository(clock=lambda: CREATED_AT)

    first = repository.create_draft_run("workspace-alpha", make_request())
    second = repository.create_draft_run("workspace-alpha", make_request())

    assert first.run_id == "draft-run-000001"
    assert second.run_id == "draft-run-000002"
    assert "/" not in first.run_id
    assert " " not in first.run_id


def test_repository_reads_are_isolated_by_workspace_and_run_id() -> None:
    repository = InMemoryBacktestShellRepository(
        run_id_factory=lambda workspace_id, request: f"{workspace_id}-run",
        clock=lambda: CREATED_AT,
    )
    alpha = repository.create_draft_run("workspace-alpha", make_request())
    beta = repository.create_draft_run("workspace-beta", make_request())

    assert repository.get_run("workspace-alpha", alpha.run_id) == alpha
    assert repository.get_run("workspace-beta", beta.run_id) == beta

    with pytest.raises(BacktestShellRunNotFoundError):
        repository.get_run("workspace-alpha", beta.run_id)


def test_repository_not_found_error_names_local_non_production_storage() -> None:
    repository = InMemoryBacktestShellRepository(clock=lambda: CREATED_AT)

    with pytest.raises(BacktestShellRunNotFoundError) as exc_info:
        repository.get_run("workspace-alpha", "missing-run")

    message = str(exc_info.value)
    assert "local/dev" in message
    assert "in-memory" in message
    assert "workspace-alpha" in message
    assert "missing-run" in message
    assert "non-production" in repository.storage_description


def test_quality_path_encodes_workspace_and_run_segments() -> None:
    repository = InMemoryBacktestShellRepository(
        run_id_factory=lambda workspace_id, request: "draft run/001",
        clock=lambda: CREATED_AT,
    )

    run = repository.create_draft_run("workspace alpha", make_request())

    assert run.quality_report_path == (
        "/workspaces/workspace%20alpha/backtests/draft%20run%2F001/quality"
    )
