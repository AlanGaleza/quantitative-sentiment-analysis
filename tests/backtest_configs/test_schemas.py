from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from quantitative_sentiment_analysis.backtest_configs.schemas import (
    BacktestConfigDetail,
    CreateBacktestConfigRequest,
    CreateDraftFromConfigRequest,
    UpdateBacktestConfigRequest,
)

TIMEFRAME_START = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
TIMEFRAME_END = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)


def test_create_config_request_matches_btcusd_backtest_timeframe_contract() -> None:
    request = CreateBacktestConfigRequest(
        name="  Baseline BTC config  ",
        timeframe_start=TIMEFRAME_START,
        timeframe_end=TIMEFRAME_END,
    )

    assert request.name == "Baseline BTC config"
    assert request.instrument == "BTCUSD"
    assert request.mode == "BACKTEST"


@pytest.mark.parametrize(
    "payload",
    [
        {
            "name": "naive time",
            "timeframe_start": "2026-06-01T12:00:00",
            "timeframe_end": "2026-06-08T12:00:00Z",
        },
        {
            "name": "bad order",
            "timeframe_start": "2026-06-08T12:00:00Z",
            "timeframe_end": "2026-06-01T12:00:00Z",
        },
        {
            "name": "too long",
            "timeframe_start": "2026-06-01T12:00:00Z",
            "timeframe_end": "2026-07-02T12:00:00Z",
        },
        {
            "name": "wrong instrument",
            "instrument": "ETHUSD",
            "timeframe_start": "2026-06-01T12:00:00Z",
            "timeframe_end": "2026-06-08T12:00:00Z",
        },
    ],
)
def test_create_config_request_rejects_invalid_scope_or_timeframe(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        CreateBacktestConfigRequest.model_validate(payload)


def test_update_config_request_allows_partial_edits_but_validates_pairs() -> None:
    name_only = UpdateBacktestConfigRequest(name="  renamed config  ")

    assert name_only.name == "renamed config"

    with pytest.raises(ValidationError):
        UpdateBacktestConfigRequest(
            timeframe_start=TIMEFRAME_END,
            timeframe_end=TIMEFRAME_START,
        )


def test_config_response_does_not_expose_owner_or_session_secret_fields() -> None:
    response = BacktestConfigDetail(
        id="config-1",
        workspace_id="workspace-alpha",
        name="Baseline",
        timeframe_start=TIMEFRAME_START,
        timeframe_end=TIMEFRAME_END,
        created_at=TIMEFRAME_START,
        updated_at=TIMEFRAME_END,
    )

    payload = response.model_dump()
    assert payload["workspace_id"] == "workspace-alpha"
    assert "password" not in str(payload).lower()
    assert "token" not in str(payload).lower()


def test_create_draft_from_config_request_forbids_unexpected_body_fields() -> None:
    assert CreateDraftFromConfigRequest.model_validate({}) == CreateDraftFromConfigRequest()

    with pytest.raises(ValidationError):
        CreateDraftFromConfigRequest.model_validate({"mode": "LIVE"})
