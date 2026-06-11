from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DirectionalBias(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


class RealizedDirection(StrEnum):
    UP = "UP"
    DOWN = "DOWN"
    FLAT = "FLAT"


class RelevanceLabel(StrEnum):
    RELEVANT = "RELEVANT"
    NOISE = "NOISE"
    IRRELEVANT = "IRRELEVANT"


class EvaluationOutcome(StrEnum):
    HIT = "HIT"
    MISS = "MISS"
    EXCLUDED = "EXCLUDED"


class HorizonUnit(StrEnum):
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"


def _require_aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone information")
    return value


class QualityHorizon(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    value: int = Field(default=4, gt=0)
    unit: HorizonUnit = HorizonUnit.HOURS


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
    later_return: float | None = None
    realized_direction: RealizedDirection | None = None
    model_version: str = Field(min_length=1)
    config_version: str = Field(min_length=1)

    @field_validator("event_timestamp")
    @classmethod
    def event_timestamp_must_be_aware(cls, value: datetime) -> datetime:
        return _require_aware_datetime(value)

    @model_validator(mode="after")
    def source_identity_required(self) -> Self:
        if self.source_id is None and self.source_name is None:
            raise ValueError("source_id or source_name is required")
        return self


class QualityChartPoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_timestamp: datetime
    sentiment_score: float = Field(ge=-1, le=1)
    later_return: float | None = None
    directional_bias: DirectionalBias
    realized_direction: RealizedDirection | None = None
    confidence: float = Field(ge=0, le=1)
    outcome: EvaluationOutcome

    @field_validator("event_timestamp")
    @classmethod
    def event_timestamp_must_be_aware(cls, value: datetime) -> datetime:
        return _require_aware_datetime(value)


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
