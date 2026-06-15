from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from quantitative_sentiment_analysis.backtest_dataset.provider import (
    DatasetProviderConfigurationError,
    DatasetProviderLimitationError,
    DatasetProviderUnavailableError,
    ProviderFetchRequest,
    ProviderRawRecord,
)

SHARPE_API_KEY_ENV = "SHARPE_API_KEY"
SHARPE_NEWS_API_URL = "https://terminal.jup.ag/api/v1/news/feed"
SHARPE_PAGE_LIMIT = 500

FetchJson = Callable[[str, Mapping[str, str]], dict[str, object]]


class SharpeTerminalClient:
    """Sharpe Terminal provider boundary for manual BACKTEST smoke checks."""

    provider_name = "Sharpe Terminal"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        fetch_json: FetchJson | None = None,
        api_url: str = SHARPE_NEWS_API_URL,
        page_limit: int = SHARPE_PAGE_LIMIT,
    ) -> None:
        if page_limit < 1:
            raise ValueError("page_limit must be positive")
        self._api_key = api_key if api_key is not None else _api_key_from_env()
        self._fetch_json = fetch_json or _stdlib_fetch_json
        self._api_url = api_url
        self._page_limit = page_limit

    @classmethod
    def from_environment(
        cls,
        *,
        fetch_json: FetchJson | None = None,
    ) -> SharpeTerminalClient:
        api_key = _api_key_from_env()
        if not api_key:
            raise DatasetProviderConfigurationError(
                f"{SHARPE_API_KEY_ENV} is required for Sharpe Terminal BACKTEST smoke checks"
            )
        return cls(api_key=api_key, fetch_json=fetch_json)

    def fetch_historical_news(
        self,
        request: ProviderFetchRequest,
    ) -> tuple[ProviderRawRecord, ...]:
        if not self._api_key:
            raise DatasetProviderLimitationError(
                provider_name=self.provider_name,
                reason="missing provider configuration",
                detail=(
                    f"Set {SHARPE_API_KEY_ENV} locally before running a "
                    "Sharpe Terminal BACKTEST smoke check."
                ),
            )

        records: list[ProviderRawRecord] = []
        offset = 0
        while True:
            payload = self._fetch_page(request=request, offset=offset)
            articles = _articles_from_payload(payload, provider_name=self.provider_name)
            for article in articles:
                if not isinstance(article, Mapping):
                    continue
                raw_record = _raw_record_from_article(article)
                if _is_inside_timeframe(raw_record, request):
                    records.append(raw_record)

            if len(articles) < self._page_limit:
                break
            offset += self._page_limit

        return tuple(records)

    def smoke_test(self, request: ProviderFetchRequest) -> bool:
        self.fetch_historical_news(request)
        return True

    def _fetch_page(
        self,
        *,
        request: ProviderFetchRequest,
        offset: int,
    ) -> dict[str, object]:
        url = self._build_news_url(request=request, offset=offset)
        try:
            return self._fetch_json(url, self._headers())
        except DatasetProviderLimitationError:
            raise
        except DatasetProviderConfigurationError:
            raise
        except DatasetProviderUnavailableError:
            raise
        except (HTTPError, URLError, OSError, ValueError) as exc:
            raise DatasetProviderUnavailableError(
                f"Sharpe Terminal BACKTEST provider request failed: {exc}"
            ) from exc

    def _build_news_url(self, *, request: ProviderFetchRequest, offset: int) -> str:
        params = {
            "limit": str(self._page_limit),
            "offset": str(offset),
            "category": "crypto",
            "coin": "BTC",
            "since": _iso_param(request.timeframe_start),
        }
        return f"{self._api_url}?{urlencode(params)}"

    def _headers(self) -> Mapping[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }


def _api_key_from_env() -> str | None:
    api_key = os.getenv(SHARPE_API_KEY_ENV)
    if api_key is None:
        return None
    api_key = api_key.strip()
    return api_key or None


def _stdlib_fetch_json(url: str, headers: Mapping[str, str]) -> dict[str, object]:
    request = Request(url, headers=dict(headers))
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _articles_from_payload(
    payload: Mapping[str, object],
    *,
    provider_name: str,
) -> list[object]:
    data = payload.get("data")
    articles = data.get("articles") if isinstance(data, Mapping) else None
    if not isinstance(articles, list):
        raise DatasetProviderLimitationError(
            provider_name=provider_name,
            reason="unexpected provider response",
            detail="Sharpe Terminal response did not include a data.articles list.",
        )
    return articles


def _raw_record_from_article(article: Mapping[str, object]) -> ProviderRawRecord:
    source = article.get("source")
    source_id: object | None = None
    source_name: object | None = None
    if isinstance(source, Mapping):
        source_id = source.get("id") or source.get("slug")
        source_name = source.get("name") or source.get("title")
    else:
        source_id = source
        source_name = source

    return {
        "id": article.get("id"),
        "published_at": (
            article.get("published")
            or article.get("published_at")
            or article.get("timestamp")
        ),
        "title": article.get("title"),
        "body": (
            article.get("summary")
            or article.get("body")
            or article.get("description")
        ),
        "source_id": source_id,
        "source_name": source_name,
        "url": article.get("url") or article.get("link"),
        "category": article.get("category"),
        "coin": (
            article.get("coin")
            or article.get("coins")
            or article.get("coin_tags")
        ),
    }


def _is_inside_timeframe(
    raw_record: ProviderRawRecord,
    request: ProviderFetchRequest,
) -> bool:
    published_at = _timestamp_or_none(raw_record.get("published_at"))
    if published_at is None:
        return True
    return request.timeframe_start <= published_at <= request.timeframe_end


def _timestamp_or_none(value: object) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return None
        return value
    if isinstance(value, str):
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return None
        return parsed
    return None


def _iso_param(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
