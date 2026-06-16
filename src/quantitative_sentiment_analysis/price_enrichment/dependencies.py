from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from quantitative_sentiment_analysis.price_enrichment.binance import BinanceKlineClient
from quantitative_sentiment_analysis.price_enrichment.provider import (
    ConfigurationFailurePriceProvider,
    FixturePriceProvider,
    HistoricalPriceProvider,
)
from quantitative_sentiment_analysis.price_enrichment.schemas import PriceCandle

QSA_RUNTIME_ENV = "QSA_RUNTIME_ENV"
QSA_PRICE_PROVIDER = "QSA_PRICE_PROVIDER"
BINANCE_PRICE_PROVIDER = "binance"
FIXTURE_PRICE_PROVIDER = "fixture"


def get_historical_price_provider() -> HistoricalPriceProvider:
    configured_provider = (
        os.getenv(QSA_PRICE_PROVIDER, BINANCE_PRICE_PROVIDER).strip().lower()
        or BINANCE_PRICE_PROVIDER
    )

    if configured_provider == BINANCE_PRICE_PROVIDER:
        return BinanceKlineClient()

    if configured_provider == FIXTURE_PRICE_PROVIDER:
        if os.getenv(QSA_RUNTIME_ENV, "").strip() != "local":
            return ConfigurationFailurePriceProvider(
                "fixture price provider requires QSA_RUNTIME_ENV=local"
            )
        return FixturePriceProvider(_local_fixture_candles())

    return ConfigurationFailurePriceProvider(
        f"price provider {configured_provider!r} is not available"
    )


def _local_fixture_candles() -> tuple[PriceCandle, ...]:
    base_time = datetime(2026, 6, 8, 0, 0, tzinfo=UTC)
    candles: list[PriceCandle] = []
    for offset in range(0, 24 * 60 + 1):
        open_time = base_time + timedelta(minutes=offset)
        close_price = 100_000.0 + (offset * 2.5)
        candles.append(
            PriceCandle(
                provider_name=FixturePriceProvider.provider_name,
                symbol="BTCUSDT",
                interval="1m",
                open_time=open_time,
                close_time=open_time + timedelta(minutes=1),
                open_price=close_price,
                high_price=close_price,
                low_price=close_price,
                close_price=close_price,
            )
        )
    return tuple(candles)
