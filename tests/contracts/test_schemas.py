from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from quantitative_sentiment_analysis.contracts import (
    BacktestRunMetadata,
    DatasetRecord,
    DirectionalBias,
    Instrument,
    RelevanceLabel,
    RunMode,
    WorkspaceRunIdentity,
)


EVENT_TIME = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
TIMEFRAME_START = datetime(2026, 6, 1, tzinfo=UTC)
TIMEFRAME_END = datetime(2026, 6, 8, tzinfo=UTC)


def make_record(**overrides: object) -> DatasetRecord:
    payload: dict[str, object] = {
        "workspace_id": "workspace-alpha",
        "run_id": "run-001",
        "record_id": "record-001",
        "timestamp": EVENT_TIME,
        "headline": "Bitcoin ETF inflows rise ahead of US session",
        "source_name": "Example Crypto News",
        "sentiment_score": 0.42,
        "directional_bias": DirectionalBias.LONG,
        "confidence": 0.81,
        "relevance": RelevanceLabel.RELEVANT,
        "model_version": "sentiment-rules-v1",
        "config_version": "dataset-config-v1",
    }
    payload.update(overrides)
    return DatasetRecord.model_validate(payload)


def make_metadata(**overrides: object) -> BacktestRunMetadata:
    payload: dict[str, object] = {
        "workspace_id": "workspace-alpha",
        "run_id": "run-001",
        "timeframe_start": TIMEFRAME_START,
        "timeframe_end": TIMEFRAME_END,
        "seed": 42,
        "model_version": "sentiment-rules-v1",
        "config_version": "dataset-config-v1",
        "input_fingerprint": "news-input-sha256",
    }
    payload.update(overrides)
    return BacktestRunMetadata.model_validate(payload)


def test_contract_enums_match_foundation_values() -> None:
    assert [item.value for item in Instrument] == ["BTCUSD"]
    assert [item.value for item in RunMode] == ["BACKTEST"]
    assert [item.value for item in DirectionalBias] == ["LONG", "SHORT", "FLAT"]
    assert [item.value for item in RelevanceLabel] == [
        "RELEVANT",
        "NOISE",
        "IRRELEVANT",
    ]


def test_workspace_run_identity_requires_non_empty_values() -> None:
    identity = WorkspaceRunIdentity(workspace_id="workspace-alpha", run_id="run-001")

    assert identity.workspace_id == "workspace-alpha"
    assert identity.run_id == "run-001"

    with pytest.raises(ValidationError):
        WorkspaceRunIdentity(workspace_id="", run_id="run-001")

    with pytest.raises(ValidationError):
        WorkspaceRunIdentity(workspace_id="workspace-alpha", run_id="")


@pytest.mark.parametrize("sentiment_score", [-1.01, float("nan"), float("inf")])
def test_dataset_record_rejects_invalid_sentiment(sentiment_score: float) -> None:
    with pytest.raises(ValidationError):
        make_record(sentiment_score=sentiment_score)


@pytest.mark.parametrize("confidence", [-0.01, 1.01, float("nan"), float("inf")])
def test_dataset_record_rejects_invalid_confidence(confidence: float) -> None:
    with pytest.raises(ValidationError):
        make_record(confidence=confidence)


def test_dataset_record_requires_source_identity_or_name() -> None:
    with pytest.raises(ValidationError):
        make_record(source_id=None, source_name=None)


def test_dataset_record_accepts_source_id_without_name() -> None:
    record = make_record(source_id="source-001", source_name=None)

    assert record.source_id == "source-001"
    assert record.source_name is None


def test_dataset_record_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError):
        make_record(timestamp=datetime(2026, 6, 8, 12, 0))


def test_dataset_record_preserves_audit_metadata() -> None:
    record = make_record(relevance=RelevanceLabel.NOISE)

    assert record.workspace_id == "workspace-alpha"
    assert record.run_id == "run-001"
    assert record.instrument is Instrument.BTCUSD
    assert record.mode is RunMode.BACKTEST
    assert record.model_version == "sentiment-rules-v1"
    assert record.config_version == "dataset-config-v1"
    assert record.relevance is RelevanceLabel.NOISE


def test_run_metadata_requires_aware_timeframe() -> None:
    with pytest.raises(ValidationError):
        make_metadata(timeframe_start=datetime(2026, 6, 1))

    with pytest.raises(ValidationError):
        make_metadata(timeframe_end=datetime(2026, 6, 8))


def test_run_metadata_rejects_reversed_timeframe() -> None:
    with pytest.raises(ValidationError):
        make_metadata(timeframe_start=TIMEFRAME_END, timeframe_end=TIMEFRAME_START)


def test_run_metadata_preserves_determinism_inputs() -> None:
    metadata = make_metadata(seed=7, input_fingerprint="abc123")

    assert metadata.workspace_id == "workspace-alpha"
    assert metadata.run_id == "run-001"
    assert metadata.instrument is Instrument.BTCUSD
    assert metadata.mode is RunMode.BACKTEST
    assert metadata.seed == 7
    assert metadata.input_fingerprint == "abc123"
