from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from quantitative_sentiment_analysis.backtest_quality.schemas import RealizedDirection
from quantitative_sentiment_analysis.contracts.schemas import require_aware_datetime


class PriceMovementStatus(StrEnum):
    RESOLVED = "RESOLVED"
    MISSING = "MISSING"


class PriceMissingReason(StrEnum):
    MISSING_EVENT_CANDLE = "MISSING_EVENT_CANDLE"
    MISSING_HORIZON_CANDLE = "MISSING_HORIZON_CANDLE"
    INVALID_EVENT_PRICE = "INVALID_EVENT_PRICE"
    INVALID_HORIZON_PRICE = "INVALID_HORIZON_PRICE"
    NON_FINITE_RETURN = "NON_FINITE_RETURN"


class PriceCandle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_name: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    interval: Literal["1m"] = "1m"
    open_time: datetime
    close_time: datetime
    open_price: float = Field(gt=0, allow_inf_nan=False)
    high_price: float = Field(gt=0, allow_inf_nan=False)
    low_price: float = Field(gt=0, allow_inf_nan=False)
    close_price: float = Field(gt=0, allow_inf_nan=False)

    @field_validator("open_time", "close_time")
    @classmethod
    def timestamps_must_be_aware_utc(cls, value: datetime) -> datetime:
        return require_aware_datetime(value).astimezone(UTC)

    @model_validator(mode="after")
    def candle_times_and_prices_must_be_consistent(self) -> Self:
        if self.close_time <= self.open_time:
            raise ValueError("close_time must be greater than open_time")
        if self.high_price < max(self.open_price, self.close_price, self.low_price):
            raise ValueError("high_price must be at least open, close, and low prices")
        if self.low_price > min(self.open_price, self.close_price, self.high_price):
            raise ValueError("low_price must be at most open, close, and high prices")
        return self


class PriceMovement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: PriceMovementStatus
    event_candle_open_time: datetime | None = None
    horizon_candle_open_time: datetime | None = None
    event_close_price: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    horizon_close_price: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    later_return: float | None = Field(default=None, allow_inf_nan=False)
    realized_direction: RealizedDirection | None = None
    missing_reason: PriceMissingReason | None = None

    @field_validator("event_candle_open_time", "horizon_candle_open_time")
    @classmethod
    def candle_times_must_be_aware_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return require_aware_datetime(value).astimezone(UTC)

    @model_validator(mode="after")
    def status_fields_must_be_consistent(self) -> Self:
        if self.status is PriceMovementStatus.RESOLVED:
            if self.missing_reason is not None:
                raise ValueError("resolved price movement must not include missing_reason")
            if (
                self.event_candle_open_time is None
                or self.horizon_candle_open_time is None
                or self.event_close_price is None
                or self.horizon_close_price is None
                or self.later_return is None
                or self.realized_direction is None
            ):
                raise ValueError("resolved price movement requires candle and return fields")
            return self

        if self.missing_reason is None:
            raise ValueError("missing price movement requires missing_reason")
        if self.later_return is not None or self.realized_direction is not None:
            raise ValueError("missing price movement must not include return fields")
        return self
