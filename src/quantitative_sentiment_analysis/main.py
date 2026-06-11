from __future__ import annotations

import os
from collections.abc import Sequence

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from quantitative_sentiment_analysis import __version__
from quantitative_sentiment_analysis.backtest_quality.router import router as quality_router

DEFAULT_LOCAL_CORS_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
)
QSA_CORS_ALLOWED_ORIGINS = "QSA_CORS_ALLOWED_ORIGINS"


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
    allowed_origins = list(
        cors_allowed_origins
        if cors_allowed_origins is not None
        else configured_cors_allowed_origins()
    )
    if allowed_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_methods=["GET"],
            allow_headers=["*"],
        )

    application.include_router(quality_router)
    application.add_api_route("/", read_root, methods=["GET"])
    application.add_api_route("/health", health_check, methods=["GET"])
    return application


def configured_cors_allowed_origins() -> tuple[str, ...]:
    configured_origins = tuple(
        origin.strip().rstrip("/")
        for origin in os.getenv(QSA_CORS_ALLOWED_ORIGINS, "").split(",")
        if origin.strip()
    )
    return configured_origins or DEFAULT_LOCAL_CORS_ORIGINS


app = create_app()
