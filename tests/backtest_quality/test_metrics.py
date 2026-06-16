from __future__ import annotations

import pytest

from quantitative_sentiment_analysis.backtest_quality import (
    DirectionalBias,
    RelevanceLabel,
)
from quantitative_sentiment_analysis.backtest_quality.metrics import (
    MAX_CHART_POINTS,
    MAX_REPRESENTATIVE_RECORDS,
    QualityReportInputError,
    build_quality_report,
)
from quantitative_sentiment_analysis.backtest_quality.schemas import (
    HorizonUnit,
    QualityHorizon,
    RealizedDirection,
)
from tests.backtest_quality.fixtures import make_quality_record, quality_records


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
    second = build_quality_report(list(reversed(quality_records()))).model_dump(
        mode="json"
    )

    assert first == second


def test_build_quality_report_echoes_explicit_horizon_without_changing_metrics() -> (
    None
):
    records = quality_records()
    default_report = build_quality_report(records)
    selected_horizon = QualityHorizon(value=1, unit=HorizonUnit.MINUTES)

    selected_report = build_quality_report(records, horizon=selected_horizon)

    assert selected_report.horizon == selected_horizon
    assert selected_report.metrics == default_report.metrics
    assert selected_report.warnings == default_report.warnings
    assert selected_report.chart_points == default_report.chart_points
    assert (
        selected_report.representative_records == default_report.representative_records
    )


def test_quality_payload_records_are_deterministically_capped() -> None:
    records = [
        make_quality_record(
            index,
            sentiment_score=0.5,
            directional_bias=DirectionalBias.LONG,
            later_return=0.01,
            realized_direction=RealizedDirection.UP,
        )
        for index in range(1, 151)
    ]

    report = build_quality_report(records)

    assert report.metrics.sample_count == 150
    assert len(report.chart_points) == MAX_CHART_POINTS
    assert len(report.representative_records) == MAX_REPRESENTATIVE_RECORDS
    assert report.chart_points[0].event_timestamp == records[0].event_timestamp
    assert report.chart_points[-1].event_timestamp == records[-1].event_timestamp
    assert report.representative_records[0].record_id == "record-001"
    assert report.representative_records[-1].record_id == "record-150"
    assert report.model_dump(mode="json") == build_quality_report(
        list(reversed(records))
    ).model_dump(mode="json")


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


def test_build_quality_report_appends_extra_warnings_deterministically() -> None:
    extra_warnings = (
        "Price provider was unavailable; price movement remains partial.",
        "Price provider was unavailable; price movement remains partial.",
        "1 record(s) missing price movement because the horizon price candle was unavailable.",
    )

    first = build_quality_report(
        quality_records(),
        extra_warnings=extra_warnings,
    )
    second = build_quality_report(
        list(reversed(quality_records())),
        extra_warnings=tuple(reversed(extra_warnings)),
    )

    assert first.warnings[-2:] == [
        "Price provider was unavailable; price movement remains partial.",
        "1 record(s) missing price movement because the horizon price candle was unavailable.",
    ]
    assert second.warnings.count(
        "Price provider was unavailable; price movement remains partial."
    ) == 1


def test_build_quality_report_requires_shared_run_metadata() -> None:
    records = quality_records()
    records[1] = make_quality_record(
        2,
        sentiment_score=-0.6,
        directional_bias=DirectionalBias.SHORT,
        later_return=-0.03,
        realized_direction=RealizedDirection.DOWN,
        run_id="run-002",
    )

    with pytest.raises(QualityReportInputError, match="run_id"):
        build_quality_report(records)
