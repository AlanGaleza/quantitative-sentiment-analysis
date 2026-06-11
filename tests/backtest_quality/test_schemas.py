from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from quantitative_sentiment_analysis.backtest_quality import (
    BacktestQualityReport,
    DirectionalBias,
    EvaluationOutcome,
    HorizonUnit,
    QualityChartPoint,
    QualityHorizon,
    QualityInputRecord,
    QualityMetrics,
    RealizedDirection,
    RelevanceLabel,
)


EVENT_TIME = datetime(2026, 6, 8, 12, 30, tzinfo=UTC)


def make_record(**overrides: object) -> QualityInputRecord:
    payload: dict[str, object] = {
        "workspace_id": "workspace-alpha",
        "run_id": "run-001",
        "record_id": "record-001",
        "event_timestamp": EVENT_TIME,
        "headline": "Bitcoin ETF inflows rise ahead of US session",
        "source_name": "Example Crypto News",
        "sentiment_score": 0.42,
        "directional_bias": DirectionalBias.LONG,
        "confidence": 0.81,
        "relevance": RelevanceLabel.RELEVANT,
        "later_return": 0.018,
        "realized_direction": RealizedDirection.UP,
        "model_version": "sentiment-rules-v1",
        "config_version": "quality-config-v1",
    }
    payload.update(overrides)
    return QualityInputRecord.model_validate(payload)


def make_metrics(**overrides: object) -> QualityMetrics:
    payload: dict[str, object] = {
        "correlation": 0.37,
        "hit_rate": 0.75,
        "sample_count": 4,
        "correlation_pair_count": 3,
        "hit_count": 3,
        "miss_count": 1,
        "missing_movement_count": 1,
        "flat_count": 1,
        "noise_count": 1,
    }
    payload.update(overrides)
    return QualityMetrics.model_validate(payload)


def make_chart_point(**overrides: object) -> QualityChartPoint:
    payload: dict[str, object] = {
        "event_timestamp": EVENT_TIME,
        "sentiment_score": 0.42,
        "later_return": 0.018,
        "directional_bias": DirectionalBias.LONG,
        "realized_direction": RealizedDirection.UP,
        "confidence": 0.81,
        "outcome": EvaluationOutcome.HIT,
    }
    payload.update(overrides)
    return QualityChartPoint.model_validate(payload)


def test_quality_horizon_defaults_to_four_hours() -> None:
    horizon = QualityHorizon()

    assert horizon.value == 4
    assert horizon.unit is HorizonUnit.HOURS


@pytest.mark.parametrize("sentiment_score", [-1.01, 1.01])
def test_input_record_rejects_sentiment_outside_bounds(sentiment_score: float) -> None:
    with pytest.raises(ValidationError):
        make_record(sentiment_score=sentiment_score)


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_input_record_rejects_confidence_outside_bounds(confidence: float) -> None:
    with pytest.raises(ValidationError):
        make_record(confidence=confidence)


@pytest.mark.parametrize(
    "directional_bias",
    [DirectionalBias.LONG, DirectionalBias.SHORT, DirectionalBias.FLAT],
)
def test_input_record_accepts_prd_directional_bias_values(
    directional_bias: DirectionalBias,
) -> None:
    record = make_record(directional_bias=directional_bias)

    assert record.directional_bias is directional_bias


def test_input_record_requires_source_identity_or_name() -> None:
    with pytest.raises(ValidationError):
        make_record(source_id=None, source_name=None)


def test_input_record_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError):
        make_record(event_timestamp=datetime(2026, 6, 8, 12, 30))


def test_report_preserves_identity_metadata_and_btcusd_backtest_contract() -> None:
    record = make_record()
    report = BacktestQualityReport(
        workspace_id=record.workspace_id,
        run_id=record.run_id,
        model_version=record.model_version,
        config_version=record.config_version,
        metrics=make_metrics(),
        warnings=["missing later movement counted as miss"],
        chart_points=[make_chart_point()],
        representative_records=[record],
    )

    assert report.workspace_id == "workspace-alpha"
    assert report.run_id == "run-001"
    assert report.instrument == "BTCUSD"
    assert report.mode == "BACKTEST"
    assert report.model_version == "sentiment-rules-v1"
    assert report.config_version == "quality-config-v1"
    assert report.representative_records[0].headline == record.headline


def test_noise_records_are_preserved_in_schema() -> None:
    record = make_record(relevance=RelevanceLabel.NOISE)
    metrics = make_metrics(noise_count=1, sample_count=0, hit_rate=None)
    report = BacktestQualityReport(
        workspace_id=record.workspace_id,
        run_id=record.run_id,
        model_version=record.model_version,
        config_version=record.config_version,
        metrics=metrics,
        representative_records=[record],
    )

    assert report.representative_records[0].relevance is RelevanceLabel.NOISE
    assert report.metrics.noise_count == 1
