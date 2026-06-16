from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime, timedelta
from math import isfinite

from quantitative_sentiment_analysis.backtest_quality.schemas import (
    HorizonUnit,
    QualityHorizon,
    RealizedDirection,
)
from quantitative_sentiment_analysis.contracts.schemas import require_aware_datetime
from quantitative_sentiment_analysis.price_enrichment.schemas import (
    PriceCandle,
    PriceMissingReason,
    PriceMovement,
    PriceMovementStatus,
)

PRICE_MOVEMENT_FLAT_EPSILON = 0.0005


def horizon_to_timedelta(horizon: QualityHorizon) -> timedelta:
    if horizon.unit is HorizonUnit.MINUTES:
        return timedelta(minutes=horizon.value)
    if horizon.unit is HorizonUnit.HOURS:
        return timedelta(hours=horizon.value)
    if horizon.unit is HorizonUnit.DAYS:
        return timedelta(days=horizon.value)
    raise ValueError(f"unsupported horizon unit: {horizon.unit}")


def floor_to_utc_minute(value: datetime) -> datetime:
    aware_value = require_aware_datetime(value)
    return aware_value.astimezone(UTC).replace(second=0, microsecond=0)


def horizon_target_open_time(
    event_timestamp: datetime,
    horizon: QualityHorizon,
) -> datetime:
    return floor_to_utc_minute(event_timestamp + horizon_to_timedelta(horizon))


def required_candle_open_times(
    event_timestamps: Iterable[datetime],
    horizon: QualityHorizon,
) -> tuple[datetime, ...]:
    required: set[datetime] = set()
    for event_timestamp in event_timestamps:
        required.add(floor_to_utc_minute(event_timestamp))
        required.add(horizon_target_open_time(event_timestamp, horizon))
    return tuple(sorted(required))


def classify_realized_direction(
    later_return: float,
    *,
    epsilon: float = PRICE_MOVEMENT_FLAT_EPSILON,
) -> RealizedDirection:
    if epsilon < 0:
        raise ValueError("epsilon must be non-negative")
    if not isfinite(later_return):
        raise ValueError("later_return must be finite")
    if later_return > epsilon:
        return RealizedDirection.UP
    if later_return < -epsilon:
        return RealizedDirection.DOWN
    return RealizedDirection.FLAT


def compute_price_movement(
    *,
    event_timestamp: datetime,
    horizon: QualityHorizon,
    candles_by_open_time: Mapping[datetime, PriceCandle],
    epsilon: float = PRICE_MOVEMENT_FLAT_EPSILON,
) -> PriceMovement:
    event_open_time = floor_to_utc_minute(event_timestamp)
    horizon_open_time = horizon_target_open_time(event_timestamp, horizon)
    candles = _candle_lookup(candles_by_open_time)
    event_candle = candles.get(event_open_time)
    horizon_candle = candles.get(horizon_open_time)

    if event_candle is None:
        return PriceMovement(
            status=PriceMovementStatus.MISSING,
            event_candle_open_time=event_open_time,
            horizon_candle_open_time=horizon_open_time,
            horizon_close_price=(
                horizon_candle.close_price if horizon_candle is not None else None
            ),
            missing_reason=PriceMissingReason.MISSING_EVENT_CANDLE,
        )
    if horizon_candle is None:
        return PriceMovement(
            status=PriceMovementStatus.MISSING,
            event_candle_open_time=event_open_time,
            horizon_candle_open_time=horizon_open_time,
            event_close_price=event_candle.close_price,
            missing_reason=PriceMissingReason.MISSING_HORIZON_CANDLE,
        )

    if event_candle.close_price <= 0:
        return PriceMovement(
            status=PriceMovementStatus.MISSING,
            event_candle_open_time=event_open_time,
            horizon_candle_open_time=horizon_open_time,
            horizon_close_price=horizon_candle.close_price,
            missing_reason=PriceMissingReason.INVALID_EVENT_PRICE,
        )
    if horizon_candle.close_price <= 0:
        return PriceMovement(
            status=PriceMovementStatus.MISSING,
            event_candle_open_time=event_open_time,
            horizon_candle_open_time=horizon_open_time,
            event_close_price=event_candle.close_price,
            missing_reason=PriceMissingReason.INVALID_HORIZON_PRICE,
        )

    later_return = (
        horizon_candle.close_price - event_candle.close_price
    ) / event_candle.close_price
    if not isfinite(later_return):
        return PriceMovement(
            status=PriceMovementStatus.MISSING,
            event_candle_open_time=event_open_time,
            horizon_candle_open_time=horizon_open_time,
            event_close_price=event_candle.close_price,
            horizon_close_price=horizon_candle.close_price,
            missing_reason=PriceMissingReason.NON_FINITE_RETURN,
        )

    return PriceMovement(
        status=PriceMovementStatus.RESOLVED,
        event_candle_open_time=event_open_time,
        horizon_candle_open_time=horizon_open_time,
        event_close_price=event_candle.close_price,
        horizon_close_price=horizon_candle.close_price,
        later_return=later_return,
        realized_direction=classify_realized_direction(
            later_return,
            epsilon=epsilon,
        ),
    )


def _candle_lookup(
    candles_by_open_time: Mapping[datetime, PriceCandle],
) -> dict[datetime, PriceCandle]:
    return {
        candle.open_time: candle
        for candle in candles_by_open_time.values()
    }
