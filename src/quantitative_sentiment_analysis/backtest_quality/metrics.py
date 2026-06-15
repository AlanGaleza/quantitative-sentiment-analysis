from __future__ import annotations

from collections.abc import Sequence
from math import sqrt

from quantitative_sentiment_analysis.backtest_quality.schemas import (
    BacktestQualityReport,
    DirectionalBias,
    EvaluationOutcome,
    QualityChartPoint,
    QualityHorizon,
    QualityInputRecord,
    QualityMetrics,
    RealizedDirection,
    RelevanceLabel,
)

MAX_REPRESENTATIVE_RECORDS = 100
MAX_CHART_POINTS = 100


class QualityReportInputError(ValueError):
    """Raised when records cannot form a deterministic quality report."""


def build_quality_report(
    records: Sequence[QualityInputRecord],
    horizon: QualityHorizon | None = None,
) -> BacktestQualityReport:
    ordered_records = sorted(
        records,
        key=lambda record: (
            record.event_timestamp.isoformat(),
            record.record_id or "",
            record.headline,
        ),
    )
    if not ordered_records:
        raise QualityReportInputError("quality report requires at least one record")

    first = ordered_records[0]
    _validate_shared_metadata(ordered_records, first)

    chart_points: list[QualityChartPoint] = []
    correlation_pairs: list[tuple[float, float]] = []
    hit_count = 0
    miss_count = 0
    missing_movement_count = 0
    flat_count = 0
    noise_count = 0

    for record in ordered_records:
        is_evaluable = record.relevance is RelevanceLabel.RELEVANT
        if not is_evaluable:
            noise_count += 1
            outcome = EvaluationOutcome.EXCLUDED
        else:
            if record.directional_bias is DirectionalBias.FLAT:
                flat_count += 1
            if record.realized_direction is None:
                missing_movement_count += 1
                miss_count += 1
                outcome = EvaluationOutcome.MISS
            elif _is_hit(record.directional_bias, record.realized_direction):
                hit_count += 1
                outcome = EvaluationOutcome.HIT
            else:
                miss_count += 1
                outcome = EvaluationOutcome.MISS

            if record.later_return is not None:
                correlation_pairs.append((record.sentiment_score, record.later_return))

        chart_points.append(
            QualityChartPoint(
                event_timestamp=record.event_timestamp,
                sentiment_score=record.sentiment_score,
                later_return=record.later_return,
                directional_bias=record.directional_bias,
                realized_direction=record.realized_direction,
                confidence=record.confidence,
                outcome=outcome,
            )
        )

    sample_count = hit_count + miss_count
    correlation = _pearson_correlation(correlation_pairs)
    metrics = QualityMetrics(
        correlation=correlation,
        hit_rate=(hit_count / sample_count) if sample_count else None,
        sample_count=sample_count,
        correlation_pair_count=len(correlation_pairs),
        hit_count=hit_count,
        miss_count=miss_count,
        missing_movement_count=missing_movement_count,
        flat_count=flat_count,
        noise_count=noise_count,
    )

    return BacktestQualityReport(
        workspace_id=first.workspace_id,
        run_id=first.run_id,
        horizon=horizon or QualityHorizon(),
        model_version=first.model_version,
        config_version=first.config_version,
        metrics=metrics,
        warnings=_build_warnings(metrics),
        chart_points=_sample_chart_points(chart_points),
        representative_records=_sample_representative_records(ordered_records),
    )


def _validate_shared_metadata(
    records: Sequence[QualityInputRecord],
    first: QualityInputRecord,
) -> None:
    for record in records:
        if record.workspace_id != first.workspace_id:
            raise QualityReportInputError("all records must share workspace_id")
        if record.run_id != first.run_id:
            raise QualityReportInputError("all records must share run_id")
        if record.model_version != first.model_version:
            raise QualityReportInputError("all records must share model_version")
        if record.config_version != first.config_version:
            raise QualityReportInputError("all records must share config_version")


def _is_hit(bias: DirectionalBias, realized: RealizedDirection) -> bool:
    return (
        (bias is DirectionalBias.LONG and realized is RealizedDirection.UP)
        or (bias is DirectionalBias.SHORT and realized is RealizedDirection.DOWN)
        or (bias is DirectionalBias.FLAT and realized is RealizedDirection.FLAT)
    )


def _pearson_correlation(pairs: Sequence[tuple[float, float]]) -> float | None:
    if len(pairs) < 2:
        return None

    sentiment_values = [pair[0] for pair in pairs]
    return_values = [pair[1] for pair in pairs]
    sentiment_mean = sum(sentiment_values) / len(sentiment_values)
    return_mean = sum(return_values) / len(return_values)
    numerator = sum(
        (sentiment - sentiment_mean) * (later_return - return_mean)
        for sentiment, later_return in pairs
    )
    sentiment_variance = sum(
        (sentiment - sentiment_mean) ** 2 for sentiment in sentiment_values
    )
    return_variance = sum(
        (later_return - return_mean) ** 2 for later_return in return_values
    )
    denominator = sqrt(sentiment_variance * return_variance)
    if denominator == 0:
        return None
    return numerator / denominator


def _sample_representative_records(
    records: Sequence[QualityInputRecord],
    max_records: int = MAX_REPRESENTATIVE_RECORDS,
) -> list[QualityInputRecord]:
    if len(records) <= max_records:
        return list(records)
    if max_records <= 0:
        return []
    if max_records == 1:
        return [records[0]]

    last_index = len(records) - 1
    return [
        records[(sample_index * last_index) // (max_records - 1)]
        for sample_index in range(max_records)
    ]


def _sample_chart_points(
    points: Sequence[QualityChartPoint],
    max_points: int = MAX_CHART_POINTS,
) -> list[QualityChartPoint]:
    if len(points) <= max_points:
        return list(points)
    if max_points <= 0:
        return []
    if max_points == 1:
        return [points[0]]

    last_index = len(points) - 1
    return [
        points[(sample_index * last_index) // (max_points - 1)]
        for sample_index in range(max_points)
    ]


def _build_warnings(metrics: QualityMetrics) -> list[str]:
    warnings: list[str] = []
    if metrics.missing_movement_count:
        warnings.append(
            f"{metrics.missing_movement_count} record(s) missing later movement "
            "were counted as misses."
        )
    if metrics.noise_count:
        warnings.append(
            f"{metrics.noise_count} noise/irrelevant record(s) were preserved "
            "but excluded from metric denominators."
        )
    if metrics.correlation is None:
        warnings.append(
            "Correlation is unavailable because fewer than two evaluable numeric "
            "return pairs exist or one side has zero variance."
        )
    return warnings
