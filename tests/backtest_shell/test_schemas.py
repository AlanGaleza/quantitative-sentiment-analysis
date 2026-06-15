from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from quantitative_sentiment_analysis.backtest_shell import (
    BacktestRunShell,
    BacktestRunStatus,
    CreateBacktestRunRequest,
)
from quantitative_sentiment_analysis.contracts import Instrument, RunMode


TIMEFRAME_START = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
TIMEFRAME_END = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
CREATED_AT = datetime(2026, 6, 8, 12, 30, tzinfo=UTC)


def make_request(**overrides: object) -> CreateBacktestRunRequest:
    payload: dict[str, object] = {
        "timeframe_start": TIMEFRAME_START,
        "timeframe_end": TIMEFRAME_END,
    }
    payload.update(overrides)
    return CreateBacktestRunRequest.model_validate(payload)


def make_shell(**overrides: object) -> BacktestRunShell:
    payload: dict[str, object] = {
        "workspace_id": "workspace-alpha",
        "run_id": "draft-run-000001",
        "timeframe_start": TIMEFRAME_START,
        "timeframe_end": TIMEFRAME_END,
        "status": BacktestRunStatus.DRAFT,
        "created_at": CREATED_AT,
        "quality_report_path": (
            "/workspaces/workspace-alpha/backtests/draft-run-000001/quality"
        ),
    }
    payload.update(overrides)
    return BacktestRunShell.model_validate(payload)


def test_create_request_defaults_to_btcusd_backtest() -> None:
    request = make_request()

    assert request.instrument is Instrument.BTCUSD
    assert request.mode is RunMode.BACKTEST
    assert request.timeframe_start == TIMEFRAME_START
    assert request.timeframe_end == TIMEFRAME_END


def test_run_shell_preserves_workspace_run_identity_and_status() -> None:
    shell = make_shell(status=BacktestRunStatus.READY_FOR_DATASET)

    assert shell.workspace_id == "workspace-alpha"
    assert shell.run_id == "draft-run-000001"
    assert shell.instrument is Instrument.BTCUSD
    assert shell.mode is RunMode.BACKTEST
    assert shell.status is BacktestRunStatus.READY_FOR_DATASET
    assert shell.quality_report_path == (
        "/workspaces/workspace-alpha/backtests/draft-run-000001/quality"
    )


@pytest.mark.parametrize(
    "field",
    ["timeframe_start", "timeframe_end"],
)
def test_create_request_rejects_naive_timeframe(field: str) -> None:
    with pytest.raises(ValidationError):
        make_request(**{field: datetime(2026, 6, 8, 12, 0)})


def test_run_shell_rejects_naive_created_at() -> None:
    with pytest.raises(ValidationError):
        make_shell(created_at=datetime(2026, 6, 8, 12, 30))


def test_create_request_rejects_reversed_timeframe() -> None:
    with pytest.raises(ValidationError, match="timeframe_end"):
        make_request(timeframe_start=TIMEFRAME_END, timeframe_end=TIMEFRAME_START)


def test_create_request_rejects_range_over_thirty_days() -> None:
    with pytest.raises(ValidationError, match="30 days"):
        make_request(timeframe_end=TIMEFRAME_START + timedelta(days=30, seconds=1))


def test_create_request_accepts_exactly_thirty_days() -> None:
    request = make_request(timeframe_end=TIMEFRAME_START + timedelta(days=30))

    assert request.timeframe_end - request.timeframe_start == timedelta(days=30)


def test_models_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        make_request(unexpected="value")

    with pytest.raises(ValidationError):
        make_shell(unexpected="value")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("instrument", "ETHUSD"),
        ("mode", "LIVE"),
    ],
)
def test_create_request_rejects_out_of_scope_enum_values(
    field: str,
    value: str,
) -> None:
    with pytest.raises(ValidationError):
        make_request(**{field: value})
