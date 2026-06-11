from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from quantitative_sentiment_analysis.backtest_quality import (
    DirectionalBias,
    RelevanceLabel,
)
from quantitative_sentiment_analysis.backtest_quality.metrics import (
    QualityReportInputError,
    build_quality_report,
)
from quantitative_sentiment_analysis.backtest_quality.schemas import (
    QualityInputRecord,
    RealizedDirection,
)


BASE_TIME = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)


def make_record(
    index: int,
    *,
    sentiment_score: float,
    directional_bias: DirectionalBias,
    later_return: float | None,
    realized_direction: RealizedDirection | None,
    relevance: RelevanceLabel = RelevanceLabel.RELEVANT,
    workspace_id: str = "workspace-alpha",
    run_id: str = "run-001",
    model_version: str = "sentiment-rules-v1",
    config_version: str = "quality-config-v1",
) -> QualityInputRecord:
    return QualityInputRecord(
        workspace_id=workspace_id,
        run_id=run_id,
        record_id=f"record-{index:03d}",
        event_timestamp=BASE_TIME + timedelta(minutes=index),
        headline=f"BTCUSD quality fixture {index}",
        source_name="Example Crypto News",
        sentiment_score=sentiment_score,
        directional_bias=directional_bias,
        confidence=0.75,
        relevance=relevance,
        later_return=later_return,
        realized_direction=realized_direction,
        model_version=model_version,
        config_version=config_version,
    )


def quality_records() -> list[QualityInputRecord]:
    return [
        make_record(
            1,
            sentiment_score=0.8,
            directional_bias=DirectionalBias.LONG,
            later_return=0.04,
            realized_direction=RealizedDirection.UP,
        ),
        make_record(
            2,
            sentiment_score=-0.6,
            directional_bias=DirectionalBias.SHORT,
            later_return=-0.03,
            realized_direction=RealizedDirection.DOWN,
        ),
        make_record(
            3,
            sentiment_score=0.0,
            directional_bias=DirectionalBias.FLAT,
            later_return=0.0,
            realized_direction=RealizedDirection.FLAT,
        ),
        make_record(
            4,
            sentiment_score=0.5,
            directional_bias=DirectionalBias.LONG,
            later_return=None,
            realized_direction=None,
        ),
        make_record(
            5,
            sentiment_score=-0.9,
            directional_bias=DirectionalBias.SHORT,
            later_return=-0.02,
            realized_direction=RealizedDirection.DOWN,
            relevance=RelevanceLabel.NOISE,
        ),
    ]


def test_build_quality_report_calculates_metrics_with_plan_semantics() -> None:
    report = build_quality_report(quality_records())

    assert report.workspace_id == "workspace-alpha"
    assert report.run_id == "run-001"
    assert report.instrument == "BTCUSD"
    assert report.mode == "BACKTEST"
    assert report.horizon.value == 4
    assert report.metrics.sample_count == 4
    assert report.metrics.hit_count == 3
    assert report.metrics.miss_count == 1
    assert report.metrics.hit_rate == 0.75
    assert report.metrics.missing_movement_count == 1
    assert report.metrics.flat_count == 1
    assert report.metrics.noise_count == 1
    assert report.metrics.correlation_pair_count == 3
    assert report.metrics.correlation is not None
    assert report.metrics.correlation > 0.99
    assert report.chart_points[-1].outcome == "EXCLUDED"
    assert report.representative_records[-1].relevance is RelevanceLabel.NOISE


def test_build_quality_report_is_deterministic() -> None:
    first = build_quality_report(quality_records()).model_dump(mode="json")
    second = build_quality_report(list(reversed(quality_records()))).model_dump(mode="json")

    assert first == second


def test_missing_later_movement_counts_as_miss() -> None:
    report = build_quality_report([quality_records()[3]])

    assert report.metrics.sample_count == 1
    assert report.metrics.hit_count == 0
    assert report.metrics.miss_count == 1
    assert report.metrics.hit_rate == 0.0
    assert report.metrics.missing_movement_count == 1
    assert "counted as misses" in report.warnings[0]


def test_noise_is_preserved_but_excluded_from_metric_denominators() -> None:
    report = build_quality_report([quality_records()[4]])

    assert report.metrics.sample_count == 0
    assert report.metrics.hit_rate is None
    assert report.metrics.noise_count == 1
    assert report.chart_points[0].outcome == "EXCLUDED"


def test_correlation_is_none_for_insufficient_pairs() -> None:
    report = build_quality_report([quality_records()[0]])

    assert report.metrics.correlation is None
    assert report.metrics.correlation_pair_count == 1
    assert any("Correlation is unavailable" in warning for warning in report.warnings)


def test_build_quality_report_requires_shared_run_metadata() -> None:
    records = quality_records()
    records[1] = make_record(
        2,
        sentiment_score=-0.6,
        directional_bias=DirectionalBias.SHORT,
        later_return=-0.03,
        realized_direction=RealizedDirection.DOWN,
        run_id="run-002",
    )

    with pytest.raises(QualityReportInputError, match="run_id"):
        build_quality_report(records)
