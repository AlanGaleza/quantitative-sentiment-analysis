"""Shared quality contracts for BTCUSD BACKTEST datasets."""

from quantitative_sentiment_analysis.contracts.safety import (
    ALLOWED_PRODUCT_TERMS,
    BANNED_PRODUCT_TERMS,
    SemanticSafetyError,
    assert_semantic_safety,
    find_banned_terms,
)
from quantitative_sentiment_analysis.contracts.schemas import (
    BacktestRunMetadata,
    DatasetRecord,
    DirectionalBias,
    Instrument,
    RelevanceLabel,
    RunMode,
    WorkspaceRunIdentity,
)
from quantitative_sentiment_analysis.contracts.serialization import (
    dataset_record_jsonl_line,
    run_fingerprint_material,
    stable_json_data,
    stable_json_dumps,
    stable_run_fingerprint,
)

__all__ = [
    "ALLOWED_PRODUCT_TERMS",
    "BANNED_PRODUCT_TERMS",
    "BacktestRunMetadata",
    "DatasetRecord",
    "DirectionalBias",
    "Instrument",
    "RelevanceLabel",
    "RunMode",
    "SemanticSafetyError",
    "WorkspaceRunIdentity",
    "assert_semantic_safety",
    "dataset_record_jsonl_line",
    "find_banned_terms",
    "run_fingerprint_material",
    "stable_json_data",
    "stable_json_dumps",
    "stable_run_fingerprint",
]
