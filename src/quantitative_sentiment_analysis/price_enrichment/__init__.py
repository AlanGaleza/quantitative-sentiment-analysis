"""Deterministic BTCUSD BACKTEST price enrichment contracts."""

from quantitative_sentiment_analysis.price_enrichment.movement import (
    PRICE_MOVEMENT_FLAT_EPSILON,
    classify_realized_direction,
    compute_price_movement,
    floor_to_utc_minute,
    horizon_target_open_time,
    horizon_to_timedelta,
    required_candle_open_times,
)
from quantitative_sentiment_analysis.price_enrichment.provider import (
    PRICE_INTERVAL_1M,
    PRICE_PROXY_SYMBOL,
    ConfigurationFailurePriceProvider,
    FixturePriceProvider,
    HistoricalPriceProvider,
    PriceFetchRequest,
    PriceProviderConfigurationError,
    PriceProviderError,
    PriceProviderLimitationError,
    PriceProviderUnavailableError,
    PriceProviderUnsupportedScopeError,
)
from quantitative_sentiment_analysis.price_enrichment.service import (
    PriceEnrichmentService,
)
from quantitative_sentiment_analysis.price_enrichment.schemas import (
    PriceCandle,
    PriceMissingReason,
    PriceMovement,
    PriceMovementStatus,
)

__all__ = [
    "PRICE_MOVEMENT_FLAT_EPSILON",
    "PRICE_INTERVAL_1M",
    "PRICE_PROXY_SYMBOL",
    "ConfigurationFailurePriceProvider",
    "FixturePriceProvider",
    "HistoricalPriceProvider",
    "PriceCandle",
    "PriceFetchRequest",
    "PriceMissingReason",
    "PriceMovement",
    "PriceMovementStatus",
    "PriceProviderConfigurationError",
    "PriceProviderError",
    "PriceProviderLimitationError",
    "PriceProviderUnavailableError",
    "PriceProviderUnsupportedScopeError",
    "PriceEnrichmentService",
    "classify_realized_direction",
    "compute_price_movement",
    "floor_to_utc_minute",
    "horizon_target_open_time",
    "horizon_to_timedelta",
    "required_candle_open_times",
]
