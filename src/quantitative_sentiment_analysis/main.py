from __future__ import annotations

import os
from collections.abc import Awaitable, Callable, Iterable, Sequence
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import Response

from quantitative_sentiment_analysis import __version__
from quantitative_sentiment_analysis.auth.router import router as auth_router
from quantitative_sentiment_analysis.auth.security import session_cookie_settings
from quantitative_sentiment_analysis.backtest_dataset.router import (
    router as dataset_router,
)
from quantitative_sentiment_analysis.backtest_quality.router import router as quality_router
from quantitative_sentiment_analysis.backtest_shell.router import router as shell_router

DEFAULT_LOCAL_CORS_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
)
QSA_CORS_ALLOWED_ORIGINS = "QSA_CORS_ALLOWED_ORIGINS"
COOKIE_AUTH_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
COOKIE_AUTH_ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
COOKIE_AUTH_ALLOWED_HEADERS = ["Accept", "Content-Type"]


def read_root() -> dict[str, str]:
    return {
        "service": "quantitative-sentiment-analysis",
        "status": "ok",
        "mode": "backtest-only",
    }


def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "quantitative-sentiment-analysis",
        "version": __version__,
    }


def create_app(cors_allowed_origins: Sequence[str] | None = None) -> FastAPI:
    application = FastAPI(
        title="Quantitative Sentiment Analysis",
        version=__version__,
        description="BACKTEST-only API for deterministic BTCUSD sentiment datasets.",
    )
    allowed_origins = normalize_cors_allowed_origins(
        cors_allowed_origins
        if cors_allowed_origins is not None
        else configured_cors_allowed_origins()
    )
    if allowed_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_methods=COOKIE_AUTH_ALLOWED_METHODS,
            allow_headers=COOKIE_AUTH_ALLOWED_HEADERS,
            allow_credentials=True,
        )
    add_cookie_auth_origin_guard(application, allowed_origins)

    application.include_router(auth_router)
    application.include_router(shell_router)
    application.include_router(dataset_router)
    application.include_router(quality_router)
    application.add_api_route("/", read_root, methods=["GET"])
    application.add_api_route("/health", health_check, methods=["GET"])
    return application


def configured_cors_allowed_origins() -> list[str]:
    configured_origins = normalize_cors_allowed_origins(
        origin.strip()
        for origin in os.getenv(QSA_CORS_ALLOWED_ORIGINS, "").split(",")
        if origin.strip()
    )
    return configured_origins or list(DEFAULT_LOCAL_CORS_ORIGINS)


def normalize_cors_allowed_origins(origins: Iterable[str]) -> list[str]:
    return [_normalize_cors_origin(origin) for origin in origins]


def add_cookie_auth_origin_guard(
    application: FastAPI,
    allowed_origins: Sequence[str],
) -> None:
    allowed_origin_set = set(allowed_origins)

    @application.middleware("http")
    async def guard_cookie_authenticated_unsafe_requests(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.method.upper() in COOKIE_AUTH_UNSAFE_METHODS and request.cookies.get(
            session_cookie_settings().name
        ):
            origin = _normalized_origin_header(request)
            if origin not in allowed_origin_set:
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": (
                            "origin is not allowed for cookie-authenticated "
                            "state changes"
                        )
                    },
                )
        return await call_next(request)


def _normalized_origin_header(request: Request) -> str | None:
    origin = request.headers.get("origin")
    if not origin:
        return None
    try:
        return _normalize_cors_origin(origin)
    except ValueError:
        return None


def _normalize_cors_origin(origin: str) -> str:
    normalized = origin.strip().rstrip("/")
    parsed = urlparse(normalized)
    if normalized == "*" or parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(
            "CORS origins must be explicit http(s) origins; wildcard origins are not allowed"
        )
    if parsed.path or parsed.params or parsed.query or parsed.fragment:
        raise ValueError("CORS origins must not include paths, queries, or fragments")
    return normalized


app = create_app()
