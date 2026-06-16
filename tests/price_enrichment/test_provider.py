from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import cast

import pytest

from quantitative_sentiment_analysis.contracts import Instrument, RunMode
from quantitative_sentiment_analysis.price_enrichment.dependencies import (
    BINANCE_PRICE_PROVIDER,
    FIXTURE_PRICE_PROVIDER,
    QSA_PRICE_PROVIDER,
    QSA_RUNTIME_ENV,
    get_historical_price_provider,
)
from quantitative_sentiment_analysis.price_enrichment.provider import (
    ConfigurationFailurePriceProvider,
    FixturePriceProvider,
    PriceFetchRequest,
    PriceProviderConfigurationError,
    PriceProviderUnsupportedScopeError,
)
from quantitative_sentiment_analysis.price_enrichment.schemas import PriceCandle

BASE_TIME = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)


def make_request(**overrides: object) -> PriceFetchRequest:
    payload: dict[str, object] = {
        "instrument": Instrument.BTCUSD,
        "mode": RunMode.BACKTEST,
        "timeframe_start": BASE_TIME,
        "timeframe_end": BASE_TIME + timedelta(minutes=2),
        "provider_metadata": {"proxy": "BTCUSD via BTCUSDT"},
    }
    payload.update(overrides)
    return PriceFetchRequest(**payload)  # type: ignore[arg-type]


def make_candle(offset: int, *, close_price: float = 100.0) -> PriceCandle:
    open_time = BASE_TIME + timedelta(minutes=offset)
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


def test_price_fetch_request_accepts_btcusd_backtest_scope_and_normalizes_utc() -> None:
    warsaw = timezone(timedelta(hours=2))
    request = make_request(
        timeframe_start=datetime(2026, 6, 16, 14, 0, tzinfo=warsaw),
        timeframe_end=datetime(2026, 6, 16, 14, 2, tzinfo=warsaw),
    )

    assert request.instrument is Instrument.BTCUSD
    assert request.mode is RunMode.BACKTEST
    assert request.symbol == "BTCUSDT"
    assert request.interval == "1m"
    assert request.timeframe_start == BASE_TIME
    assert request.timeframe_end == BASE_TIME + timedelta(minutes=2)
    assert request.provider_metadata == {"proxy": "BTCUSD via BTCUSDT"}


def test_price_fetch_request_rejects_unsupported_scope() -> None:
    with pytest.raises(PriceProviderUnsupportedScopeError, match="BTCUSD"):
        make_request(instrument=cast(Instrument, "ETHUSD"))

    with pytest.raises(PriceProviderUnsupportedScopeError, match="BACKTEST"):
        make_request(mode=cast(RunMode, "LIVE"))

    with pytest.raises(PriceProviderUnsupportedScopeError, match="BTCUSDT"):
        make_request(symbol=cast(object, "BTCBUSD"))

    with pytest.raises(PriceProviderUnsupportedScopeError, match="1m"):
        make_request(interval=cast(object, "5m"))


def test_price_fetch_request_requires_aware_ordered_timeframe() -> None:
    with pytest.raises(ValueError, match="timezone"):
        make_request(timeframe_start=datetime(2026, 6, 16, 12, 0))

    with pytest.raises(ValueError, match="greater than or equal"):
        make_request(
            timeframe_start=BASE_TIME + timedelta(minutes=1),
            timeframe_end=BASE_TIME,
        )


def test_fixture_price_provider_returns_copied_records_inside_requested_window() -> None:
    provider = FixturePriceProvider(
        [
            make_candle(-1, close_price=99.0),
            make_candle(0, close_price=100.0),
            make_candle(2, close_price=102.0),
            make_candle(3, close_price=103.0),
        ]
    )

    first = provider.fetch_price_candles(make_request())
    second = provider.fetch_price_candles(make_request())

    assert provider.provider_name == "FixturePrice"
    assert [candle.close_price for candle in first] == [100.0, 102.0]
    assert second == first
    assert second is not first


def test_default_price_provider_is_binance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(QSA_PRICE_PROVIDER, raising=False)

    provider = get_historical_price_provider()

    assert provider.provider_name == "Binance Spot"


def test_fixture_price_provider_is_local_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(QSA_PRICE_PROVIDER, FIXTURE_PRICE_PROVIDER)
    monkeypatch.setenv(QSA_RUNTIME_ENV, "local")

    provider = get_historical_price_provider()

    assert isinstance(provider, FixturePriceProvider)
    assert provider.fetch_price_candles(
        PriceFetchRequest(
            instrument=Instrument.BTCUSD,
            mode=RunMode.BACKTEST,
            timeframe_start=datetime(2026, 6, 8, 0, 0, tzinfo=UTC),
            timeframe_end=datetime(2026, 6, 8, 0, 2, tzinfo=UTC),
        )
    )


def test_fixture_price_provider_rejects_non_local_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(QSA_PRICE_PROVIDER, FIXTURE_PRICE_PROVIDER)
    monkeypatch.setenv(QSA_RUNTIME_ENV, "production")

    provider = get_historical_price_provider()

    assert isinstance(provider, ConfigurationFailurePriceProvider)
    with pytest.raises(PriceProviderConfigurationError, match=QSA_RUNTIME_ENV):
        provider.fetch_price_candles(make_request())


def test_unknown_price_provider_degrades_to_typed_configuration_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(QSA_PRICE_PROVIDER, "mystery")

    provider = get_historical_price_provider()

    assert isinstance(provider, ConfigurationFailurePriceProvider)
    with pytest.raises(PriceProviderConfigurationError, match="mystery"):
        provider.fetch_price_candles(make_request())


def test_explicit_binance_provider_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(QSA_PRICE_PROVIDER, BINANCE_PRICE_PROVIDER)

    provider = get_historical_price_provider()

    assert provider.provider_name == "Binance Spot"
