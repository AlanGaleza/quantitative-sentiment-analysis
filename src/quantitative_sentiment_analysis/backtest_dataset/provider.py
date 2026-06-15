from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, TypeAlias

from quantitative_sentiment_analysis.backtest_dataset.schemas import (
    DatasetProviderLimitation,
)
from quantitative_sentiment_analysis.contracts import Instrument, RunMode
from quantitative_sentiment_analysis.contracts.schemas import require_aware_datetime

ProviderRawRecord: TypeAlias = Mapping[str, object]


class DatasetProviderError(RuntimeError):
    """Base class for deterministic BACKTEST news provider failures."""


class DatasetProviderConfigurationError(DatasetProviderError):
    """Raised when the configured provider cannot run because config is missing."""


class DatasetProviderUnavailableError(DatasetProviderError):
    """Raised when the configured provider is temporarily unavailable."""


class DatasetProviderUnsupportedScopeError(DatasetProviderError):
    """Raised when a provider is asked for non-BTCUSD BACKTEST scope."""


class DatasetProviderLimitationError(DatasetProviderError):
    """Raised when provider access cannot support the requested BACKTEST dataset."""

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
        message = f"{provider_name} provider limitation: {reason}"
        if detail:
            message = f"{message}. {detail}"
        super().__init__(message)

    def to_schema(self) -> DatasetProviderLimitation:
        return DatasetProviderLimitation(
            provider_name=self.provider_name,
            reason=self.reason,
            detail=self.detail,
        )


@dataclass(frozen=True)
class ProviderFetchRequest:
    workspace_id: str
    run_id: str
    instrument: Instrument
    mode: RunMode
    timeframe_start: datetime
    timeframe_end: datetime

    def __post_init__(self) -> None:
        if not self.workspace_id:
            raise ValueError("workspace_id is required")
        if not self.run_id:
            raise ValueError("run_id is required")
        if self.instrument is not Instrument.BTCUSD:
            raise DatasetProviderUnsupportedScopeError("provider supports only BTCUSD")
        if self.mode is not RunMode.BACKTEST:
            raise DatasetProviderUnsupportedScopeError("provider supports only BACKTEST")
        require_aware_datetime(self.timeframe_start)
        require_aware_datetime(self.timeframe_end)
        if self.timeframe_end < self.timeframe_start:
            raise ValueError("timeframe_end must be greater than or equal to timeframe_start")


class HistoricalNewsProvider(Protocol):
    provider_name: str

    def fetch_historical_news(
        self,
        request: ProviderFetchRequest,
    ) -> tuple[ProviderRawRecord, ...]:
        """Return raw historical provider records for deterministic BACKTEST use."""
        ...


class FixtureNewsProvider:
    """Offline provider for deterministic tests; never calls the live network."""

    provider_name = "FixtureNews"

    def __init__(self, records: Sequence[ProviderRawRecord]) -> None:
        self._records = tuple(dict(record) for record in records)

    def fetch_historical_news(
        self,
        request: ProviderFetchRequest,
    ) -> tuple[ProviderRawRecord, ...]:
        return tuple(dict(record) for record in self._records)
