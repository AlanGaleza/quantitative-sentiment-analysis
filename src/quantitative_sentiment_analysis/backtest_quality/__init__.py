"""Backtest quality report contracts."""

from quantitative_sentiment_analysis.backtest_quality.metrics import build_quality_report
from quantitative_sentiment_analysis.backtest_quality.repository import (
    NotReadyQualityInputProvider,
    QualityInputProvider,
    QualityRunIncompleteError,
    QualityRunNotFoundError,
    QualityRunNotReadyError,
    QualityRunUnsupportedError,
    get_quality_input_provider,
)
from quantitative_sentiment_analysis.backtest_quality.schemas import (
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

__all__ = [
    "BacktestQualityReport",
    "DirectionalBias",
    "EvaluationOutcome",
    "HorizonUnit",
    "NotReadyQualityInputProvider",
    "QualityChartPoint",
    "QualityHorizon",
    "QualityInputProvider",
    "QualityInputRecord",
    "QualityMetrics",
    "QualityRunIncompleteError",
    "QualityRunNotFoundError",
    "QualityRunNotReadyError",
    "QualityRunUnsupportedError",
    "RealizedDirection",
    "RelevanceLabel",
    "build_quality_report",
    "get_quality_input_provider",
]
