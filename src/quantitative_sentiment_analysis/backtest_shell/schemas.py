from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from quantitative_sentiment_analysis.contracts import Instrument, RunMode
from quantitative_sentiment_analysis.contracts.schemas import require_aware_datetime

MAX_BACKTEST_RANGE_DAYS = 30
MAX_BACKTEST_RANGE = timedelta(days=MAX_BACKTEST_RANGE_DAYS)


class BacktestRunStatus(StrEnum):
    DRAFT = "DRAFT"
    READY_FOR_DATASET = "READY_FOR_DATASET"


class CreateBacktestRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    instrument: Instrument = Instrument.BTCUSD
    mode: RunMode = RunMode.BACKTEST
    timeframe_start: datetime
    timeframe_end: datetime

    @field_validator("timeframe_start", "timeframe_end")
    @classmethod
    def timestamps_must_be_aware(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)

    @model_validator(mode="after")
    def must_be_btcusd_backtest_with_valid_timeframe(self) -> Self:
        _require_btcusd_backtest(self.instrument, self.mode)
        _require_valid_backtest_timeframe(self.timeframe_start, self.timeframe_end)
        return self


class BacktestRunShell(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    instrument: Instrument = Instrument.BTCUSD
    mode: RunMode = RunMode.BACKTEST
    timeframe_start: datetime
    timeframe_end: datetime
    status: BacktestRunStatus = BacktestRunStatus.DRAFT
    created_at: datetime
    quality_report_path: str | None = None

    @field_validator("timeframe_start", "timeframe_end", "created_at")
    @classmethod
    def timestamps_must_be_aware(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)

    @model_validator(mode="after")
    def must_be_btcusd_backtest_with_valid_timeframe(self) -> Self:
        _require_btcusd_backtest(self.instrument, self.mode)
        _require_valid_backtest_timeframe(self.timeframe_start, self.timeframe_end)
        return self


def _require_btcusd_backtest(instrument: Instrument, mode: RunMode) -> None:
    if instrument is not Instrument.BTCUSD:
        raise ValueError("instrument must be BTCUSD")
    if mode is not RunMode.BACKTEST:
        raise ValueError("mode must be BACKTEST")


def _require_valid_backtest_timeframe(
    timeframe_start: datetime,
    timeframe_end: datetime,
) -> None:
    if timeframe_end < timeframe_start:
        raise ValueError("timeframe_end must be greater than or equal to timeframe_start")
    if timeframe_end - timeframe_start > MAX_BACKTEST_RANGE:
        raise ValueError(
            f"BACKTEST timeframe range must be no more than {MAX_BACKTEST_RANGE_DAYS} days"
        )
