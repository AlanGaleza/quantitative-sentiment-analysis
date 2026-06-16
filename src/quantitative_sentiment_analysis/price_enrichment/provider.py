from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal, Protocol

from quantitative_sentiment_analysis.contracts import Instrument, RunMode
from quantitative_sentiment_analysis.contracts.schemas import require_aware_datetime
from quantitative_sentiment_analysis.price_enrichment.schemas import PriceCandle

PRICE_PROXY_SYMBOL: Literal["BTCUSDT"] = "BTCUSDT"
PRICE_INTERVAL_1M: Literal["1m"] = "1m"


class PriceProviderError(RuntimeError):
    """Base class for deterministic BACKTEST price provider failures."""


class PriceProviderConfigurationError(PriceProviderError):
    """Raised when the configured price provider cannot run."""


class PriceProviderUnavailableError(PriceProviderError):
    """Raised when the configured price provider is temporarily unavailable."""


class PriceProviderUnsupportedScopeError(PriceProviderError):
    """Raised when a provider is asked for non-BTCUSD BACKTEST price data."""


class PriceProviderLimitationError(PriceProviderError):
    """Raised when provider data cannot support the requested price enrichment."""

    def __init__(
        self,
        *,
        provider_name: str,
        reason: str,
        detail: str | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.reason = reason
        self.detail = detail
        message = f"{provider_name} price provider limitation: {reason}"
        if detail:
            message = f"{message}. {detail}"
        super().__init__(message)


@dataclass(frozen=True)
class PriceFetchRequest:
    instrument: Instrument
    mode: RunMode
    timeframe_start: datetime
    timeframe_end: datetime
    symbol: Literal["BTCUSDT"] = PRICE_PROXY_SYMBOL
    interval: Literal["1m"] = PRICE_INTERVAL_1M
    provider_metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.instrument is not Instrument.BTCUSD:
            raise PriceProviderUnsupportedScopeError(
                "price provider supports only BTCUSD"
            )
        if self.mode is not RunMode.BACKTEST:
            raise PriceProviderUnsupportedScopeError(
                "price provider supports only BACKTEST"
            )
        if self.symbol != PRICE_PROXY_SYMBOL:
            raise PriceProviderUnsupportedScopeError(
                f"price provider supports only {PRICE_PROXY_SYMBOL}"
            )
        if self.interval != PRICE_INTERVAL_1M:
            raise PriceProviderUnsupportedScopeError(
                f"price provider supports only {PRICE_INTERVAL_1M} candles"
            )

        start = require_aware_datetime(self.timeframe_start).astimezone(UTC)
        end = require_aware_datetime(self.timeframe_end).astimezone(UTC)
        if end < start:
            raise ValueError(
                "timeframe_end must be greater than or equal to timeframe_start"
            )

        object.__setattr__(self, "timeframe_start", start)
        object.__setattr__(self, "timeframe_end", end)
        object.__setattr__(self, "provider_metadata", dict(self.provider_metadata))


class HistoricalPriceProvider(Protocol):
    provider_name: str

    def fetch_price_candles(
        self,
        request: PriceFetchRequest,
    ) -> tuple[PriceCandle, ...]:
        """Return historical candles for deterministic BACKTEST price enrichment."""
        ...


class FixturePriceProvider:
    """Offline price provider for deterministic tests; never calls the live network."""

    provider_name = "FixturePrice"

    def __init__(self, candles: Sequence[PriceCandle] = ()) -> None:
        self._candles = tuple(_copy_candle(candle) for candle in candles)

    def fetch_price_candles(
        self,
        request: PriceFetchRequest,
    ) -> tuple[PriceCandle, ...]:
        return tuple(
            _copy_candle(candle)
            for candle in self._candles
            if candle.symbol == request.symbol
            and candle.interval == request.interval
            and request.timeframe_start <= candle.open_time <= request.timeframe_end
        )


class ConfigurationFailurePriceProvider:
    """Provider placeholder that defers config failures to the enrichment boundary."""

    provider_name = "UnavailablePriceProvider"

    def __init__(self, message: str) -> None:
        self.message = message

    def fetch_price_candles(
        self,
        request: PriceFetchRequest,
    ) -> tuple[PriceCandle, ...]:
        raise PriceProviderConfigurationError(self.message)


def _copy_candle(candle: PriceCandle) -> PriceCandle:
    return PriceCandle.model_validate(candle.model_dump())
