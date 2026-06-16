from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import TypeAlias, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pydantic import ValidationError

from quantitative_sentiment_analysis.price_enrichment.provider import (
    PRICE_INTERVAL_1M,
    PriceFetchRequest,
    PriceProviderConfigurationError,
    PriceProviderLimitationError,
    PriceProviderUnavailableError,
)
from quantitative_sentiment_analysis.price_enrichment.schemas import PriceCandle

BINANCE_SPOT_PROVIDER_NAME = "Binance Spot"
BINANCE_SPOT_BASE_URL = "https://api.binance.com"
BINANCE_KLINES_PATH = "/api/v3/klines"
BINANCE_KLINE_LIMIT = 1000
ONE_MINUTE_MS = 60_000

FetchJson: TypeAlias = Callable[[str, Mapping[str, str]], object]


class BinanceKlineClient:
    """Binance Spot kline provider boundary for BTCUSDT proxy candles."""

    provider_name = BINANCE_SPOT_PROVIDER_NAME

    def __init__(
        self,
        *,
        fetch_json: FetchJson | None = None,
        base_url: str = BINANCE_SPOT_BASE_URL,
        page_limit: int = BINANCE_KLINE_LIMIT,
    ) -> None:
        if page_limit < 1 or page_limit > BINANCE_KLINE_LIMIT:
            raise ValueError(
                f"page_limit must be between 1 and {BINANCE_KLINE_LIMIT}"
            )
        normalized_base_url = base_url.rstrip("/")
        if not normalized_base_url:
            raise PriceProviderConfigurationError("Binance base URL is required")

        self._fetch_json = fetch_json or _stdlib_fetch_json
        self._base_url = normalized_base_url
        self._page_limit = page_limit

    def fetch_price_candles(
        self,
        request: PriceFetchRequest,
    ) -> tuple[PriceCandle, ...]:
        start_ms = _milliseconds(request.timeframe_start)
        end_ms = _milliseconds(request.timeframe_end)
        current_start_ms = start_ms
        candles_by_open_time: dict[datetime, PriceCandle] = {}

        while current_start_ms <= end_ms:
            payload = self._fetch_page(
                request=request,
                start_time_ms=current_start_ms,
                end_time_ms=end_ms,
            )
            page_candles = _candles_from_payload(
                payload,
                provider_name=self.provider_name,
                symbol=request.symbol,
                interval=request.interval,
            )
            if not page_candles:
                break

            for candle in page_candles:
                if request.timeframe_start <= candle.open_time <= request.timeframe_end:
                    candles_by_open_time[candle.open_time] = candle

            if len(page_candles) < self._page_limit:
                break

            next_start_ms = _milliseconds(page_candles[-1].open_time) + ONE_MINUTE_MS
            if next_start_ms <= current_start_ms:
                raise PriceProviderLimitationError(
                    provider_name=self.provider_name,
                    reason="unexpected provider response",
                    detail="Binance kline pagination did not advance.",
                )
            current_start_ms = next_start_ms

        return tuple(
            candles_by_open_time[open_time]
            for open_time in sorted(candles_by_open_time)
        )

    def _fetch_page(
        self,
        *,
        request: PriceFetchRequest,
        start_time_ms: int,
        end_time_ms: int,
    ) -> object:
        url = self._build_klines_url(
            request=request,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
        )
        try:
            return self._fetch_json(url, self._headers())
        except (
            PriceProviderConfigurationError,
            PriceProviderLimitationError,
            PriceProviderUnavailableError,
        ):
            raise
        except (HTTPError, URLError, OSError) as exc:
            raise PriceProviderUnavailableError(
                f"Binance Spot price provider request failed: {exc}"
            ) from exc
        except ValueError as exc:
            raise PriceProviderLimitationError(
                provider_name=self.provider_name,
                reason="unexpected provider response",
                detail=f"Binance Spot kline response could not be parsed: {exc}",
            ) from exc

    def _build_klines_url(
        self,
        *,
        request: PriceFetchRequest,
        start_time_ms: int,
        end_time_ms: int,
    ) -> str:
        params = {
            "symbol": request.symbol,
            "interval": request.interval,
            "startTime": str(start_time_ms),
            "endTime": str(end_time_ms),
            "limit": str(self._page_limit),
        }
        return f"{self._base_url}{BINANCE_KLINES_PATH}?{urlencode(params)}"

    def _headers(self) -> Mapping[str, str]:
        return {"Accept": "application/json"}


def _stdlib_fetch_json(url: str, headers: Mapping[str, str]) -> object:
    request = Request(url, headers=dict(headers))
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _candles_from_payload(
    payload: object,
    *,
    provider_name: str,
    symbol: str,
    interval: str,
) -> tuple[PriceCandle, ...]:
    if not isinstance(payload, list):
        raise PriceProviderLimitationError(
            provider_name=provider_name,
            reason="unexpected provider response",
            detail="Binance Spot kline response was not a list.",
        )

    candles = [
        _candle_from_kline(
            row,
            provider_name=provider_name,
            symbol=symbol,
            interval=interval,
        )
        for row in payload
    ]
    return tuple(sorted(candles, key=lambda candle: candle.open_time))


def _candle_from_kline(
    row: object,
    *,
    provider_name: str,
    symbol: str,
    interval: str,
) -> PriceCandle:
    if not _is_kline_sequence(row):
        raise PriceProviderLimitationError(
            provider_name=provider_name,
            reason="unexpected provider response",
            detail="Binance Spot kline row did not contain the expected fields.",
        )

    kline_row = cast(Sequence[object], row)
    try:
        return PriceCandle(
            provider_name=provider_name,
            symbol=symbol,
            interval=PRICE_INTERVAL_1M,
            open_time=_datetime_from_milliseconds(kline_row[0]),
            close_time=_datetime_from_milliseconds(kline_row[6]),
            open_price=_price_float(kline_row[1]),
            high_price=_price_float(kline_row[2]),
            low_price=_price_float(kline_row[3]),
            close_price=_price_float(kline_row[4]),
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise PriceProviderLimitationError(
            provider_name=provider_name,
            reason="invalid candle data",
            detail=f"Binance Spot kline row could not be validated: {exc}",
        ) from exc


def _is_kline_sequence(row: object) -> bool:
    return isinstance(row, Sequence) and not isinstance(row, str | bytes) and len(row) >= 7


def _datetime_from_milliseconds(value: object) -> datetime:
    if not isinstance(value, int):
        raise TypeError("kline time must be an integer millisecond timestamp")
    return datetime.fromtimestamp(value / 1000, tz=UTC)


def _price_float(value: object) -> float:
    if not isinstance(value, int | float | str):
        raise TypeError("kline price must be a number or decimal string")
    return float(value)


def _milliseconds(value: datetime) -> int:
    return int(value.astimezone(UTC).timestamp() * 1000)
