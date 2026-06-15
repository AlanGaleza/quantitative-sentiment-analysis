from quantitative_sentiment_analysis.contracts.schemas import Instrument, RunMode
from quantitative_sentiment_analysis.sentiment_policy import DEFAULT_POLICY_CONFIG


def test_policy_config_locks_f02_decisions() -> None:
    assert DEFAULT_POLICY_CONFIG.provider_name == "Sharpe Terminal"
    assert DEFAULT_POLICY_CONFIG.instrument is Instrument.BTCUSD
    assert DEFAULT_POLICY_CONFIG.mode is RunMode.BACKTEST
    assert DEFAULT_POLICY_CONFIG.default_historical_range_days == 30
    assert DEFAULT_POLICY_CONFIG.default_quality_horizon_hours == 4
    assert DEFAULT_POLICY_CONFIG.long_threshold == 0.20
    assert DEFAULT_POLICY_CONFIG.short_threshold == -0.20
    assert DEFAULT_POLICY_CONFIG.model_version
    assert DEFAULT_POLICY_CONFIG.config_version


def test_policy_config_import_requires_no_provider_secret() -> None:
    assert "token" not in DEFAULT_POLICY_CONFIG.__dict__
    assert "secret" not in DEFAULT_POLICY_CONFIG.__dict__
    assert "key" not in DEFAULT_POLICY_CONFIG.__dict__
