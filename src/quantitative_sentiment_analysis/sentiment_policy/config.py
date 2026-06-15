from __future__ import annotations

from dataclasses import dataclass

from quantitative_sentiment_analysis.contracts.schemas import Instrument, RunMode


@dataclass(frozen=True)
class SentimentPolicyConfig:
    provider_name: str = "Sharpe Terminal"
    instrument: Instrument = Instrument.BTCUSD
    mode: RunMode = RunMode.BACKTEST
    default_historical_range_days: int = 30
    default_quality_horizon_hours: int = 4
    long_threshold: float = 0.20
    short_threshold: float = -0.20
    model_version: str = "sentiment-rules-v1"
    config_version: str = "news-sentiment-policy-v1"


DEFAULT_POLICY_CONFIG = SentimentPolicyConfig()
