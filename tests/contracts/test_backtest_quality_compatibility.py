from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from quantitative_sentiment_analysis.auth.dependencies import require_owned_workspace
from quantitative_sentiment_analysis.backtest_quality import (
    DirectionalBias as QualityDirectionalBias,
)
from quantitative_sentiment_analysis.backtest_quality import (
    QualityInputRecord,
    RelevanceLabel as QualityRelevanceLabel,
    get_quality_input_provider,
)
from quantitative_sentiment_analysis.contracts import (
    DatasetRecord,
    DirectionalBias,
    RelevanceLabel,
)
from quantitative_sentiment_analysis.main import app
from tests.backtest_quality.fixtures import FixtureQualityInputProvider


EVENT_TIME = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)


def make_quality_record(**overrides: object) -> QualityInputRecord:
    payload: dict[str, object] = {
        "workspace_id": "workspace-alpha",
        "run_id": "run-001",
        "record_id": "record-001",
        "event_timestamp": EVENT_TIME,
        "headline": "Bitcoin ETF inflows rise ahead of US session",
        "source_name": "Example Crypto News",
        "sentiment_score": 0.42,
        "directional_bias": QualityDirectionalBias.LONG,
        "confidence": 0.81,
        "relevance": QualityRelevanceLabel.RELEVANT,
        "later_return": 0.018,
        "model_version": "sentiment-rules-v1",
        "config_version": "quality-config-v1",
    }
    payload.update(overrides)
    return QualityInputRecord.model_validate(payload)


def test_backtest_quality_enums_are_shared_contract_aliases() -> None:
    assert QualityDirectionalBias is DirectionalBias
    assert QualityRelevanceLabel is RelevanceLabel
    assert QualityDirectionalBias.LONG.value == "LONG"
    assert QualityRelevanceLabel.NOISE.value == "NOISE"


def test_quality_input_record_maps_to_foundation_dataset_record() -> None:
    quality_record = make_quality_record(source_id="source-001", source_name=None)

    dataset_record = DatasetRecord.model_validate(
        {
            "workspace_id": quality_record.workspace_id,
            "run_id": quality_record.run_id,
            "record_id": quality_record.record_id,
            "timestamp": quality_record.event_timestamp,
            "headline": quality_record.headline,
            "source_id": quality_record.source_id,
            "source_name": quality_record.source_name,
            "instrument": quality_record.instrument,
            "mode": quality_record.mode,
            "sentiment_score": quality_record.sentiment_score,
            "directional_bias": quality_record.directional_bias,
            "confidence": quality_record.confidence,
            "relevance": quality_record.relevance,
            "model_version": quality_record.model_version,
            "config_version": quality_record.config_version,
        }
    )

    assert dataset_record.timestamp == quality_record.event_timestamp
    assert dataset_record.source_id == "source-001"
    assert dataset_record.source_name is None
    assert dataset_record.workspace_id == quality_record.workspace_id
    assert dataset_record.run_id == quality_record.run_id
    assert dataset_record.model_version == quality_record.model_version
    assert dataset_record.config_version == quality_record.config_version


def test_quality_route_preserves_s04_response_shape() -> None:
    app.dependency_overrides[require_owned_workspace] = lambda: object()
    app.dependency_overrides[get_quality_input_provider] = (
        lambda: FixtureQualityInputProvider()
    )
    try:
        client = TestClient(app)
        response = client.get("/api/workspaces/workspace-alpha/backtests/run-001/quality")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["workspace_id"] == "workspace-alpha"
    assert data["run_id"] == "run-001"
    assert data["instrument"] == "BTCUSD"
    assert data["mode"] == "BACKTEST"
    assert data["model_version"] == "sentiment-rules-v1"
    assert data["config_version"] == "quality-config-v1"
    assert "chart_points" in data
    assert "representative_records" in data
    assert "event_timestamp" in data["chart_points"][0]
    assert "timestamp" not in data["chart_points"][0]
    assert "event_timestamp" in data["representative_records"][0]
    assert "timestamp" not in data["representative_records"][0]
