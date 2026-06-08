from __future__ import annotations

from fastapi import FastAPI

from quantitative_sentiment_analysis import __version__

app = FastAPI(
    title="Quantitative Sentiment Analysis",
    version=__version__,
    description="BACKTEST-only API for deterministic BTCUSD sentiment datasets.",
)


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "service": "quantitative-sentiment-analysis",
        "status": "ok",
        "mode": "backtest-only",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "quantitative-sentiment-analysis",
        "version": __version__,
    }
