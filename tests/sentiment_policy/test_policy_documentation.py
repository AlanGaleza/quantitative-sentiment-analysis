from pathlib import Path


POLICY_TEXT = Path("context/foundation/news-sentiment-policy.md").read_text()


def test_policy_document_contains_load_bearing_f02_decisions() -> None:
    for expected in [
        "Sharpe Terminal",
        "30-day",
        "0.20",
        "-0.20",
        "4 hours",
        "RELEVANT",
        "NOISE",
        "IRRELEVANT",
        "classification confidence",
    ]:
        assert expected in POLICY_TEXT


def test_policy_document_requires_sampled_or_limited_quality_payloads() -> None:
    assert "sampled sentiment-vs-later-return plot" in POLICY_TEXT
    assert "chart and detail" in POLICY_TEXT
    assert "payloads must be bounded" in POLICY_TEXT


def test_policy_document_requires_sharpe_smoke_test() -> None:
    assert "Sharpe Terminal token/API smoke" in POLICY_TEXT
