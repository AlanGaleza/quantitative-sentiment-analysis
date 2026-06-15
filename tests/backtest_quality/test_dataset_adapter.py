from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from quantitative_sentiment_analysis.backtest_dataset import (
    DatasetProviderLimitation,
    DatasetRunStatus,
    DatasetRunSummary,
    InMemoryCompletedDatasetRepository,
)
from quantitative_sentiment_analysis.backtest_quality import (
    CompletedDatasetQualityInputProvider,
    QualityRunIncompleteError,
    QualityRunNotFoundError,
    get_quality_input_provider,
)
from quantitative_sentiment_analysis.contracts import (
    DatasetRecord,
    DirectionalBias,
    RelevanceLabel,
)
from quantitative_sentiment_analysis.main import app

TIMEFRAME_START = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
TIMEFRAME_END = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
EVENT_TIME = datetime(2026, 6, 2, 9, 30, tzinfo=UTC)


def make_summary(**overrides: object) -> DatasetRunSummary:
    payload: dict[str, object] = {
        "workspace_id": "workspace-alpha",
        "run_id": "draft-run-fixed",
        "timeframe_start": TIMEFRAME_START,
        "timeframe_end": TIMEFRAME_END,
        "status": DatasetRunStatus.COMPLETED,
        "provider_name": "FixtureNews",
        "record_count": 2,
        "relevant_count": 1,
        "noise_count": 1,
        "irrelevant_count": 0,
        "model_version": "sentiment-rules-v1",
        "config_version": "news-sentiment-policy-v1",
        "input_fingerprint": "fingerprint-alpha",
    }
    payload.update(overrides)
    return DatasetRunSummary.model_validate(payload)


def make_record(index: int, **overrides: object) -> DatasetRecord:
    payload: dict[str, object] = {
        "workspace_id": "workspace-alpha",
        "run_id": "draft-run-fixed",
        "record_id": f"record-{index:03d}",
        "timestamp": EVENT_TIME,
        "headline": f"Bitcoin ETF approval headline {index}",
        "source_name": "FixtureNews",
        "sentiment_score": 0.45,
        "directional_bias": DirectionalBias.LONG,
        "confidence": 0.72,
        "relevance": RelevanceLabel.RELEVANT,
        "model_version": "sentiment-rules-v1",
        "config_version": "news-sentiment-policy-v1",
    }
    payload.update(overrides)
    return DatasetRecord.model_validate(payload)


def make_repository() -> InMemoryCompletedDatasetRepository:
    repository = InMemoryCompletedDatasetRepository()
    repository.save_run(
        make_summary(),
        [
            make_record(1),
            make_record(
                2,
                headline="Provider placeholder",
                sentiment_score=0.0,
                directional_bias=DirectionalBias.FLAT,
                relevance=RelevanceLabel.NOISE,
            ),
        ],
    )
    return repository


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_adapter_maps_canonical_dataset_records_to_quality_inputs() -> None:
    provider = CompletedDatasetQualityInputProvider(make_repository())

    records = provider.get_quality_inputs("workspace-alpha", "draft-run-fixed")

    assert len(records) == 2
    assert records[0].workspace_id == "workspace-alpha"
    assert records[0].run_id == "draft-run-fixed"
    assert records[0].event_timestamp == EVENT_TIME
    assert records[0].later_return is None
    assert records[0].realized_direction is None
    assert records[0].directional_bias is DirectionalBias.LONG
    assert records[0].model_version == "sentiment-rules-v1"
    assert records[1].relevance is RelevanceLabel.NOISE


def test_quality_route_reads_completed_dataset_and_reports_missing_movement() -> None:
    repository = make_repository()
    app.dependency_overrides[get_quality_input_provider] = (
        lambda: CompletedDatasetQualityInputProvider(repository)
    )
    client = TestClient(app)

    response = client.get(
        "/api/workspaces/workspace-alpha/backtests/draft-run-fixed/quality"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["workspace_id"] == "workspace-alpha"
    assert data["run_id"] == "draft-run-fixed"
    assert data["model_version"] == "sentiment-rules-v1"
    assert data["config_version"] == "news-sentiment-policy-v1"
    assert data["metrics"]["missing_movement_count"] == 1
    assert data["metrics"]["noise_count"] == 1
    assert any("missing later movement" in warning for warning in data["warnings"])
    assert data["representative_records"][0]["later_return"] is None
    assert data["representative_records"][0]["realized_direction"] is None


def test_adapter_isolates_workspace_and_run() -> None:
    provider = CompletedDatasetQualityInputProvider(make_repository())

    with pytest.raises(QualityRunNotFoundError):
        provider.get_quality_inputs("workspace-beta", "draft-run-fixed")

    with pytest.raises(QualityRunNotFoundError):
        provider.get_quality_inputs("workspace-alpha", "other-run")


def test_adapter_rejects_incomplete_or_provider_limited_runs() -> None:
    repository = InMemoryCompletedDatasetRepository()
    repository.save_run(
        make_summary(
            status=DatasetRunStatus.FAILED_PROVIDER_LIMITATION,
            record_count=0,
            relevant_count=0,
            noise_count=0,
            provider_limitation=DatasetProviderLimitation(
                provider_name="Sharpe Terminal",
                reason="missing provider configuration",
            ),
        ),
        [],
    )
    provider = CompletedDatasetQualityInputProvider(repository)

    with pytest.raises(QualityRunIncompleteError, match="completed BACKTEST dataset"):
        provider.get_quality_inputs("workspace-alpha", "draft-run-fixed")


def test_adapter_rejects_completed_empty_dataset() -> None:
    repository = InMemoryCompletedDatasetRepository()
    repository.save_run(
        make_summary(record_count=0, relevant_count=0, noise_count=0),
        [],
    )
    provider = CompletedDatasetQualityInputProvider(repository)

    with pytest.raises(QualityRunIncompleteError, match="no records"):
        provider.get_quality_inputs("workspace-alpha", "draft-run-fixed")
