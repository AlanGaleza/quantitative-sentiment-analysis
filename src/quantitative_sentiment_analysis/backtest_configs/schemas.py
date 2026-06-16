from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from quantitative_sentiment_analysis.backtest_shell.schemas import (
    CreateBacktestRunRequest,
)
from quantitative_sentiment_analysis.contracts import Instrument, RunMode
from quantitative_sentiment_analysis.contracts.schemas import require_aware_datetime


class CreateBacktestConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=255)
    instrument: Instrument = Instrument.BTCUSD
    mode: RunMode = RunMode.BACKTEST
    timeframe_start: datetime
    timeframe_end: datetime

    @field_validator("name")
    @classmethod
    def name_must_be_trimmed(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be empty")
        return stripped

    @field_validator("timeframe_start", "timeframe_end")
    @classmethod
    def timestamps_must_be_aware(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)

    @model_validator(mode="after")
    def must_match_backtest_run_contract(self) -> Self:
        CreateBacktestRunRequest(
            instrument=self.instrument,
            mode=self.mode,
            timeframe_start=self.timeframe_start,
            timeframe_end=self.timeframe_end,
        )
        return self


class UpdateBacktestConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    instrument: Instrument | None = None
    mode: RunMode | None = None
    timeframe_start: datetime | None = None
    timeframe_end: datetime | None = None

    @field_validator("name")
    @classmethod
    def name_must_be_trimmed(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be empty")
        return stripped

    @field_validator("timeframe_start", "timeframe_end")
    @classmethod
    def timestamps_must_be_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return require_aware_datetime(value)

    @model_validator(mode="after")
    def provided_scope_must_be_backtest_only(self) -> Self:
        if self.instrument is not None and self.instrument is not Instrument.BTCUSD:
            raise ValueError("instrument must be BTCUSD")
        if self.mode is not None and self.mode is not RunMode.BACKTEST:
            raise ValueError("mode must be BACKTEST")
        if self.timeframe_start is not None and self.timeframe_end is not None:
            CreateBacktestRunRequest(
                timeframe_start=self.timeframe_start,
                timeframe_end=self.timeframe_end,
            )
        return self


class BacktestConfigListItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    workspace_id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=255)
    instrument: Instrument = Instrument.BTCUSD
    mode: RunMode = RunMode.BACKTEST
    timeframe_start: datetime
    timeframe_end: datetime
    created_at: datetime
    updated_at: datetime

    @field_validator(
        "timeframe_start",
        "timeframe_end",
        "created_at",
        "updated_at",
    )
    @classmethod
    def timestamps_must_be_aware(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)


class BacktestConfigDetail(BacktestConfigListItem):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CreateDraftFromConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
