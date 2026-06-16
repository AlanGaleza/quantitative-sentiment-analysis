from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

import pytest

from quantitative_sentiment_analysis.contracts import Instrument, RunMode
from quantitative_sentiment_analysis.price_enrichment.binance import (
    BINANCE_KLINES_PATH,
    BinanceKlineClient,
)
from quantitative_sentiment_analysis.price_enrichment.provider import (
    PriceFetchRequest,
    PriceProviderLimitationError,
    PriceProviderUnavailableError,
)

BASE_TIME = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)


def make_request(
    *,
    start: datetime = BASE_TIME,
    end: datetime = BASE_TIME + timedelta(minutes=1),
) -> PriceFetchRequest:
    return PriceFetchRequest(
        instrument=Instrument.BTCUSD,
        mode=RunMode.BACKTEST,
        timeframe_start=start,
        timeframe_end=end,
    )


def kline(
    offset: int,
    *,
    open_price: str = "100.0",
    high_price: str = "101.0",
    low_price: str = "99.0",
    close_price: str = "100.5",
) -> list[object]:
    open_time = BASE_TIME + timedelta(minutes=offset)
    close_time = open_time + timedelta(minutes=1) - timedelta(milliseconds=1)
    return [
        int(open_time.timestamp() * 1000),
        open_price,
        high_price,
        low_price,
        close_price,
        "10.0",
        int(close_time.timestamp() * 1000),
        "1000.0",
        42,
        "5.0",
        "500.0",
        "0",
    ]


def test_binance_fetch_uses_expected_url_query_and_headers() -> None:
    requested: list[tuple[str, dict[str, str]]] = []

    def fetch_json(url: str, headers: Mapping[str, str]) -> object:
        requested.append((url, dict(headers)))
        return [kline(0), kline(1)]

    client = BinanceKlineClient(
        fetch_json=fetch_json,
        base_url="https://binance.test",
    )

    candles = client.fetch_price_candles(make_request())

    assert [candle.close_price for candle in candles] == [100.5, 100.5]
    url, headers = requested[0]
    assert headers == {"Accept": "application/json"}
    parsed_url = urlparse(url)
    assert parsed_url.scheme == "https"
    assert parsed_url.netloc == "binance.test"
    assert parsed_url.path == BINANCE_KLINES_PATH
    query = parse_qs(parsed_url.query)
    assert query["symbol"] == ["BTCUSDT"]
    assert query["interval"] == ["1m"]
    assert query["startTime"] == [str(int(BASE_TIME.timestamp() * 1000))]
    assert query["endTime"] == [
        str(int((BASE_TIME + timedelta(minutes=1)).timestamp() * 1000))
    ]
    assert query["limit"] == ["1000"]


def test_binance_fetch_paginates_when_limit_sized_page_is_returned() -> None:
    requested_start_times: list[str] = []

    def fetch_json(url: str, headers: Mapping[str, str]) -> object:
        query = parse_qs(urlparse(url).query)
        requested_start_times.append(query["startTime"][0])
        if len(requested_start_times) == 1:
            return [kline(0), kline(1)]
        return [kline(2)]

    client = BinanceKlineClient(
        fetch_json=fetch_json,
        base_url="https://binance.test",
        page_limit=2,
    )

    candles = client.fetch_price_candles(
        make_request(end=BASE_TIME + timedelta(minutes=2))
    )

    assert requested_start_times == [
        str(int(BASE_TIME.timestamp() * 1000)),
        str(int((BASE_TIME + timedelta(minutes=2)).timestamp() * 1000)),
    ]
    assert [candle.open_time for candle in candles] == [
        BASE_TIME,
        BASE_TIME + timedelta(minutes=1),
        BASE_TIME + timedelta(minutes=2),
    ]


def test_binance_fetch_parses_candles_into_deterministic_output_order() -> None:
    client = BinanceKlineClient(
        fetch_json=lambda url, headers: [
            kline(1, high_price="102.0", close_price="101.5"),
            kline(0),
        ],
        base_url="https://binance.test",
    )

    candles = client.fetch_price_candles(make_request())

    assert [candle.open_time for candle in candles] == [
        BASE_TIME,
        BASE_TIME + timedelta(minutes=1),
    ]
    assert candles[0].provider_name == "Binance Spot"
    assert candles[0].symbol == "BTCUSDT"
    assert candles[0].interval == "1m"
    assert candles[0].open_price == 100.0
    assert candles[0].high_price == 101.0
    assert candles[0].low_price == 99.0
    assert candles[0].close_price == 100.5


def test_binance_fetch_filters_candles_outside_requested_window() -> None:
    client = BinanceKlineClient(
        fetch_json=lambda url, headers: [kline(-1), kline(0), kline(2)],
        base_url="https://binance.test",
    )

    candles = client.fetch_price_candles(make_request())

    assert [candle.open_time for candle in candles] == [BASE_TIME]


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "ok"},
        ["unexpected"],
        [[int(BASE_TIME.timestamp() * 1000), "100.0"]],
    ],
)
def test_binance_malformed_response_is_provider_limitation(payload: object) -> None:
    client = BinanceKlineClient(
        fetch_json=lambda url, headers: payload,
        base_url="https://binance.test",
    )

    with pytest.raises(PriceProviderLimitationError, match="unexpected provider response"):
        client.fetch_price_candles(make_request())


@pytest.mark.parametrize(
    "bad_kline",
    [
        kline(0, open_price="nan"),
        kline(0, close_price="0"),
        kline(0, high_price="98.0"),
        kline(0, low_price="-1.0"),
    ],
)
def test_binance_invalid_prices_are_provider_limitation(
    bad_kline: list[object],
) -> None:
    client = BinanceKlineClient(
        fetch_json=lambda url, headers: [bad_kline],
        base_url="https://binance.test",
    )

    with pytest.raises(PriceProviderLimitationError, match="invalid candle data"):
        client.fetch_price_candles(make_request())


def test_binance_http_or_url_failures_are_unavailable() -> None:
    def fetch_json(url: str, headers: Mapping[str, str]) -> object:
        raise URLError("network unavailable")

    client = BinanceKlineClient(
        fetch_json=fetch_json,
        base_url="https://binance.test",
    )

    with pytest.raises(PriceProviderUnavailableError, match="request failed"):
        client.fetch_price_candles(make_request())


def test_binance_client_rejects_invalid_page_limit() -> None:
    with pytest.raises(ValueError, match="page_limit"):
        BinanceKlineClient(page_limit=0)

    with pytest.raises(ValueError, match="page_limit"):
        BinanceKlineClient(page_limit=1001)
