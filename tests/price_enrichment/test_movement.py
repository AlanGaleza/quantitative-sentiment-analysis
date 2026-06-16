from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from quantitative_sentiment_analysis.backtest_quality.schemas import (
    HorizonUnit,
    QualityHorizon,
    RealizedDirection,
)
from quantitative_sentiment_analysis.price_enrichment import (
    PRICE_MOVEMENT_FLAT_EPSILON,
    PriceCandle,
    PriceMissingReason,
    PriceMovementStatus,
    classify_realized_direction,
    compute_price_movement,
    floor_to_utc_minute,
    horizon_target_open_time,
    horizon_to_timedelta,
    required_candle_open_times,
)


BASE_TIME = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)


def make_candle(open_time: datetime, *, close_price: float) -> PriceCandle:
    return PriceCandle(
        provider_name="FixturePrice",
        symbol="BTCUSDT",
        interval="1m",
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1),
        open_price=close_price,
        high_price=close_price,
        low_price=close_price,
        close_price=close_price,
    )


def test_price_candle_normalizes_aware_times_to_utc() -> None:
    warsaw = timezone(timedelta(hours=2))
    candle = make_candle(
        datetime(2026, 6, 16, 14, 0, tzinfo=warsaw),
        close_price=100.0,
    )

    assert candle.open_time == BASE_TIME
    assert candle.close_time == BASE_TIME + timedelta(minutes=1)


def test_price_candle_rejects_naive_times() -> None:
    with pytest.raises(ValidationError):
        make_candle(datetime(2026, 6, 16, 12, 0), close_price=100.0)


@pytest.mark.parametrize(
    "overrides",
    [
        {"open_price": 0.0},
        {"high_price": float("nan")},
        {"low_price": -1.0},
        {"close_price": float("inf")},
    ],
)
def test_price_candle_rejects_non_positive_or_non_finite_prices(
    overrides: dict[str, float],
) -> None:
    payload = {
        "provider_name": "FixturePrice",
        "symbol": "BTCUSDT",
        "interval": "1m",
        "open_time": BASE_TIME,
        "close_time": BASE_TIME + timedelta(minutes=1),
        "open_price": 100.0,
        "high_price": 101.0,
        "low_price": 99.0,
        "close_price": 100.5,
    }
    payload.update(overrides)

    with pytest.raises(ValidationError):
        PriceCandle.model_validate(payload)


def test_price_candle_rejects_inconsistent_high_low_values() -> None:
    with pytest.raises(ValidationError, match="high_price"):
        PriceCandle(
            provider_name="FixturePrice",
            symbol="BTCUSDT",
            open_time=BASE_TIME,
            close_time=BASE_TIME + timedelta(minutes=1),
            open_price=100.0,
            high_price=99.0,
            low_price=98.0,
            close_price=100.0,
        )

    with pytest.raises(ValidationError, match="low_price"):
        PriceCandle(
            provider_name="FixturePrice",
            symbol="BTCUSDT",
            open_time=BASE_TIME,
            close_time=BASE_TIME + timedelta(minutes=1),
            open_price=100.0,
            high_price=101.0,
            low_price=100.5,
            close_price=100.0,
        )


@pytest.mark.parametrize(
    ("horizon", "expected"),
    [
        (QualityHorizon(value=1, unit=HorizonUnit.MINUTES), timedelta(minutes=1)),
        (QualityHorizon(value=15, unit=HorizonUnit.MINUTES), timedelta(minutes=15)),
        (QualityHorizon(value=1, unit=HorizonUnit.HOURS), timedelta(hours=1)),
        (QualityHorizon(value=4, unit=HorizonUnit.HOURS), timedelta(hours=4)),
        (QualityHorizon(value=24, unit=HorizonUnit.HOURS), timedelta(hours=24)),
    ],
)
def test_horizon_to_timedelta_covers_supported_presets(
    horizon: QualityHorizon,
    expected: timedelta,
) -> None:
    assert horizon_to_timedelta(horizon) == expected


def test_floor_to_utc_minute_converts_timezone_and_drops_seconds() -> None:
    warsaw = timezone(timedelta(hours=2))

    assert floor_to_utc_minute(
        datetime(2026, 6, 16, 14, 0, 59, 999999, tzinfo=warsaw),
    ) == BASE_TIME


def test_horizon_target_open_time_adds_horizon_before_flooring() -> None:
    event_time = BASE_TIME.replace(second=45)
    horizon = QualityHorizon(value=1, unit=HorizonUnit.MINUTES)

    assert horizon_target_open_time(event_time, horizon) == (
        BASE_TIME + timedelta(minutes=1)
    )


def test_required_candle_open_times_returns_sorted_unique_event_and_horizon_times() -> (
    None
):
    horizon = QualityHorizon(value=1, unit=HorizonUnit.MINUTES)

    required = required_candle_open_times(
        [
            BASE_TIME.replace(second=30),
            (BASE_TIME + timedelta(minutes=1)).replace(second=10),
            BASE_TIME.replace(second=59),
        ],
        horizon,
    )

    assert required == (
        BASE_TIME,
        BASE_TIME + timedelta(minutes=1),
        BASE_TIME + timedelta(minutes=2),
    )


@pytest.mark.parametrize(
    ("later_return", "expected"),
    [
        (PRICE_MOVEMENT_FLAT_EPSILON + 0.000001, RealizedDirection.UP),
        (PRICE_MOVEMENT_FLAT_EPSILON, RealizedDirection.FLAT),
        (0.0, RealizedDirection.FLAT),
        (-PRICE_MOVEMENT_FLAT_EPSILON, RealizedDirection.FLAT),
        (-PRICE_MOVEMENT_FLAT_EPSILON - 0.000001, RealizedDirection.DOWN),
    ],
)
def test_classify_realized_direction_uses_epsilon_threshold(
    later_return: float,
    expected: RealizedDirection,
) -> None:
    assert classify_realized_direction(later_return) is expected


@pytest.mark.parametrize("later_return", [float("nan"), float("inf"), float("-inf")])
def test_classify_realized_direction_rejects_non_finite_return(
    later_return: float,
) -> None:
    with pytest.raises(ValueError, match="finite"):
        classify_realized_direction(later_return)


def test_compute_price_movement_uses_close_to_close_return() -> None:
    event_candle = make_candle(BASE_TIME, close_price=100.0)
    horizon_candle = make_candle(BASE_TIME + timedelta(minutes=1), close_price=101.0)

    movement = compute_price_movement(
        event_timestamp=BASE_TIME.replace(second=30),
        horizon=QualityHorizon(value=1, unit=HorizonUnit.MINUTES),
        candles_by_open_time={
            horizon_candle.open_time: horizon_candle,
            event_candle.open_time: event_candle,
        },
    )

    assert movement.status is PriceMovementStatus.RESOLVED
    assert movement.event_candle_open_time == BASE_TIME
    assert movement.horizon_candle_open_time == BASE_TIME + timedelta(minutes=1)
    assert movement.event_close_price == 100.0
    assert movement.horizon_close_price == 101.0
    assert movement.later_return == pytest.approx(0.01)
    assert movement.realized_direction is RealizedDirection.UP
    assert movement.missing_reason is None


def test_compute_price_movement_returns_missing_when_event_candle_is_absent() -> None:
    horizon_candle = make_candle(BASE_TIME + timedelta(minutes=1), close_price=101.0)

    movement = compute_price_movement(
        event_timestamp=BASE_TIME.replace(second=30),
        horizon=QualityHorizon(value=1, unit=HorizonUnit.MINUTES),
        candles_by_open_time={horizon_candle.open_time: horizon_candle},
    )

    assert movement.status is PriceMovementStatus.MISSING
    assert movement.missing_reason is PriceMissingReason.MISSING_EVENT_CANDLE
    assert movement.later_return is None
    assert movement.realized_direction is None


def test_compute_price_movement_returns_missing_when_horizon_candle_is_absent() -> None:
    event_candle = make_candle(BASE_TIME, close_price=100.0)

    movement = compute_price_movement(
        event_timestamp=BASE_TIME.replace(second=30),
        horizon=QualityHorizon(value=1, unit=HorizonUnit.MINUTES),
        candles_by_open_time={event_candle.open_time: event_candle},
    )

    assert movement.status is PriceMovementStatus.MISSING
    assert movement.missing_reason is PriceMissingReason.MISSING_HORIZON_CANDLE
    assert movement.later_return is None
    assert movement.realized_direction is None


def test_compute_price_movement_rejects_invalid_event_price_defensively() -> None:
    event_candle = PriceCandle.model_construct(
        provider_name="FixturePrice",
        symbol="BTCUSDT",
        interval="1m",
        open_time=BASE_TIME,
        close_time=BASE_TIME + timedelta(minutes=1),
        open_price=0.0,
        high_price=0.0,
        low_price=0.0,
        close_price=0.0,
    )
    horizon_candle = make_candle(BASE_TIME + timedelta(minutes=1), close_price=101.0)

    movement = compute_price_movement(
        event_timestamp=BASE_TIME.replace(second=30),
        horizon=QualityHorizon(value=1, unit=HorizonUnit.MINUTES),
        candles_by_open_time={
            event_candle.open_time: event_candle,
            horizon_candle.open_time: horizon_candle,
        },
    )

    assert movement.status is PriceMovementStatus.MISSING
    assert movement.missing_reason is PriceMissingReason.INVALID_EVENT_PRICE


def test_compute_price_movement_is_deterministic() -> None:
    event_candle = make_candle(BASE_TIME, close_price=100.0)
    horizon_candle = make_candle(BASE_TIME + timedelta(minutes=4), close_price=99.0)
    horizon = QualityHorizon(value=4, unit=HorizonUnit.MINUTES)

    first = compute_price_movement(
        event_timestamp=BASE_TIME.replace(second=30),
        horizon=horizon,
        candles_by_open_time={
            event_candle.open_time: event_candle,
            horizon_candle.open_time: horizon_candle,
        },
    ).model_dump(mode="json")
    second = compute_price_movement(
        event_timestamp=BASE_TIME.replace(second=30),
        horizon=horizon,
        candles_by_open_time={
            horizon_candle.open_time: horizon_candle,
            event_candle.open_time: event_candle,
        },
    ).model_dump(mode="json")

    assert first == second
