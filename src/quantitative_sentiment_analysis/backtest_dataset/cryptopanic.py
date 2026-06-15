from __future__ import annotations

import json
import os
from collections.abc import Callable
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

CRYPTOPANIC_API_KEY_ENV = "CRYPTOPANIC_API_KEY"
CRYPTOPANIC_API_URL = "https://cryptopanic.com/api/v1/posts/"

FetchJson = Callable[[str], dict[str, object]]


class CryptoPanicClient:
    """CryptoPanic provider boundary for manual BACKTEST smoke checks."""

    provider_name = "CryptoPanic"

    def __init__(
        self,
        *,
        auth_token: str | None = None,
        fetch_json: FetchJson | None = None,
        api_url: str = CRYPTOPANIC_API_URL,
    ) -> None:
        self._auth_token = auth_token if auth_token is not None else _token_from_env()
        self._fetch_json = fetch_json or _stdlib_fetch_json
        self._api_url = api_url

    @classmethod
    def from_environment(
        cls,
        *,
        fetch_json: FetchJson | None = None,
    ) -> CryptoPanicClient:
        token = _token_from_env()
        if not token:
            raise DatasetProviderConfigurationError(
                f"{CRYPTOPANIC_API_KEY_ENV} is required for CryptoPanic BACKTEST smoke checks"
            )
        return cls(auth_token=token, fetch_json=fetch_json)

    def fetch_historical_news(
        self,
        request: ProviderFetchRequest,
    ) -> tuple[ProviderRawRecord, ...]:
        if not self._auth_token:
            raise DatasetProviderLimitationError(
                provider_name=self.provider_name,
                reason="missing provider configuration",
                detail=(
                    f"Set {CRYPTOPANIC_API_KEY_ENV} locally before running a "
                    "CryptoPanic BACKTEST smoke check."
                ),
            )

        url = self._build_posts_url(request)
        try:
            payload = self._fetch_json(url)
        except DatasetProviderLimitationError:
            raise
        except DatasetProviderConfigurationError:
            raise
        except DatasetProviderUnavailableError:
            raise
        except (HTTPError, URLError, OSError, ValueError) as exc:
            raise DatasetProviderUnavailableError(
                f"CryptoPanic BACKTEST provider request failed: {exc}"
            ) from exc

        results = payload.get("results")
        if not isinstance(results, list):
            raise DatasetProviderLimitationError(
                provider_name=self.provider_name,
                reason="unexpected provider response",
                detail="CryptoPanic response did not include a results list.",
            )
        return tuple(record for record in results if isinstance(record, dict))

    def smoke_test(self, request: ProviderFetchRequest) -> bool:
        self.fetch_historical_news(request)
        return True

    def _build_posts_url(self, request: ProviderFetchRequest) -> str:
        params = {
            "auth_token": self._auth_token,
            "currencies": "BTC",
            "public": "true",
            "kind": "news",
            "filter": "rising",
            "metadata": "true",
            "regions": "en",
            "from": _date_param(request.timeframe_start),
            "to": _date_param(request.timeframe_end),
        }
        return f"{self._api_url}?{urlencode(params)}"


def _token_from_env() -> str | None:
    token = os.getenv(CRYPTOPANIC_API_KEY_ENV)
    if token is None:
        return None
    token = token.strip()
    return token or None


def _stdlib_fetch_json(url: str) -> dict[str, object]:
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _date_param(value: datetime) -> str:
    return value.astimezone(UTC).date().isoformat()
