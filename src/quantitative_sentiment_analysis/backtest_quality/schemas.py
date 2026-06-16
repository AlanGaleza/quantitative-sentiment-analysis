from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from quantitative_sentiment_analysis.contracts.schemas import (
    DirectionalBias,
    RelevanceLabel,
    require_aware_datetime,
)


class RealizedDirection(StrEnum):
    UP = "UP"
    DOWN = "DOWN"
    FLAT = "FLAT"


class EvaluationOutcome(StrEnum):
    HIT = "HIT"
    MISS = "MISS"
    EXCLUDED = "EXCLUDED"


class HorizonUnit(StrEnum):
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"


class QualityHorizon(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    value: int = Field(default=4, gt=0)
    unit: HorizonUnit = HorizonUnit.HOURS


class UnsupportedQualityHorizonError(ValueError):
    """Raised when a requested quality report horizon is outside V1 presets."""


SUPPORTED_QUALITY_HORIZON_PRESETS: tuple[tuple[int, HorizonUnit], ...] = (
    (1, HorizonUnit.MINUTES),
    (15, HorizonUnit.MINUTES),
    (1, HorizonUnit.HOURS),
    (4, HorizonUnit.HOURS),
    (24, HorizonUnit.HOURS),
)


def supported_quality_horizon(value: int, unit: HorizonUnit) -> QualityHorizon:
    horizon = QualityHorizon(value=value, unit=unit)
    if (horizon.value, horizon.unit) not in SUPPORTED_QUALITY_HORIZON_PRESETS:
        supported = ", ".join(
            _horizon_preset_label(preset_value, preset_unit)
            for preset_value, preset_unit in SUPPORTED_QUALITY_HORIZON_PRESETS
        )
        raise UnsupportedQualityHorizonError(
            f"unsupported quality horizon; supported presets: {supported}"
        )
    return horizon


def _horizon_preset_label(value: int, unit: HorizonUnit) -> str:
    if value == 1:
        return f"1 {unit.value.removesuffix('s')}"
    return f"{value} {unit.value}"


class QualityInputRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    record_id: str | None = None
    instrument: Literal["BTCUSD"] = "BTCUSD"
    mode: Literal["BACKTEST"] = "BACKTEST"
    event_timestamp: datetime
    headline: str = Field(min_length=1)
    source_id: str | None = None
    source_name: str | None = None
    sentiment_score: float = Field(ge=-1, le=1)
    directional_bias: DirectionalBias
    confidence: float = Field(ge=0, le=1)
    relevance: RelevanceLabel = RelevanceLabel.RELEVANT
    later_return: float | None = Field(default=None, allow_inf_nan=False)
    realized_direction: RealizedDirection | None = None
    model_version: str = Field(min_length=1)
    config_version: str = Field(min_length=1)

    @field_validator("event_timestamp")
    @classmethod
    def event_timestamp_must_be_aware(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)

    @model_validator(mode="after")
    def source_identity_required(self) -> Self:
        if self.source_id is None and self.source_name is None:
            raise ValueError("source_id or source_name is required")
        return self


class QualityChartPoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_timestamp: datetime
    sentiment_score: float = Field(ge=-1, le=1)
    later_return: float | None = Field(default=None, allow_inf_nan=False)
    directional_bias: DirectionalBias
    realized_direction: RealizedDirection | None = None
    confidence: float = Field(ge=0, le=1)
    outcome: EvaluationOutcome

    @field_validator("event_timestamp")
    @classmethod
    def event_timestamp_must_be_aware(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)


class QualityMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    correlation: float | None = Field(default=None, ge=-1, le=1)
    hit_rate: float | None = Field(default=None, ge=0, le=1)
    sample_count: int = Field(ge=0)
    correlation_pair_count: int = Field(ge=0)
    hit_count: int = Field(ge=0)
    miss_count: int = Field(ge=0)
    missing_movement_count: int = Field(ge=0)
    flat_count: int = Field(ge=0)
    noise_count: int = Field(ge=0)


class BacktestQualityReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    instrument: Literal["BTCUSD"] = "BTCUSD"
    mode: Literal["BACKTEST"] = "BACKTEST"
    horizon: QualityHorizon = Field(default_factory=QualityHorizon)
    model_version: str = Field(min_length=1)
    config_version: str = Field(min_length=1)
    metrics: QualityMetrics
    warnings: list[str] = Field(default_factory=list)
    chart_points: list[QualityChartPoint] = Field(default_factory=list)
    representative_records: list[QualityInputRecord] = Field(default_factory=list)
