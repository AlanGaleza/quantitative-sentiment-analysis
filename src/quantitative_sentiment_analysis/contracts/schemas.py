from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Instrument(StrEnum):
    BTCUSD = "BTCUSD"


class RunMode(StrEnum):
    BACKTEST = "BACKTEST"


class DirectionalBias(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


class RelevanceLabel(StrEnum):
    RELEVANT = "RELEVANT"
    NOISE = "NOISE"
    IRRELEVANT = "IRRELEVANT"


def require_aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone information")
    return value


class WorkspaceRunIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)


class BacktestRunMetadata(WorkspaceRunIdentity):
    model_config = ConfigDict(extra="forbid", frozen=True)

    instrument: Instrument = Instrument.BTCUSD
    mode: RunMode = RunMode.BACKTEST
    timeframe_start: datetime
    timeframe_end: datetime
    seed: int
    model_version: str = Field(min_length=1)
    config_version: str = Field(min_length=1)
    input_fingerprint: str = Field(min_length=1)

    @field_validator("timeframe_start", "timeframe_end")
    @classmethod
    def timestamps_must_be_aware(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)

    @model_validator(mode="after")
    def timeframe_must_be_ordered(self) -> Self:
        if self.timeframe_end < self.timeframe_start:
            raise ValueError("timeframe_end must be greater than or equal to timeframe_start")
        return self


class DatasetRecord(WorkspaceRunIdentity):
    model_config = ConfigDict(extra="forbid", frozen=True)

    record_id: str | None = None
    timestamp: datetime
    headline: str = Field(min_length=1)
    source_id: str | None = None
    source_name: str | None = None
    instrument: Instrument = Instrument.BTCUSD
    mode: RunMode = RunMode.BACKTEST
    sentiment_score: float = Field(ge=-1, le=1, allow_inf_nan=False)
    directional_bias: DirectionalBias
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    relevance: RelevanceLabel = RelevanceLabel.RELEVANT
    model_version: str = Field(min_length=1)
    config_version: str = Field(min_length=1)

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_aware(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)

    @model_validator(mode="after")
    def source_identity_required(self) -> Self:
        if self.source_id is None and self.source_name is None:
            raise ValueError("source_id or source_name is required")
        return self
