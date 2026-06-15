"""Deterministic BACKTEST news dataset contracts and local/dev storage."""

from quantitative_sentiment_analysis.backtest_dataset.repository import (
    CompletedDatasetRepository,
    CompletedDatasetRunIncompleteError,
    CompletedDatasetRunNotFoundError,
    CompletedDatasetRunUnsupportedError,
    InMemoryCompletedDatasetRepository,
    get_completed_dataset_repository,
)
from quantitative_sentiment_analysis.backtest_dataset.schemas import (
    MAX_DATASET_PREVIEW_RECORDS,
    DatasetProviderLimitation,
    DatasetRunPreview,
    DatasetRunStatus,
    DatasetRunSummary,
)
from quantitative_sentiment_analysis.backtest_dataset.provider import (
    DatasetProviderConfigurationError,
    DatasetProviderError,
    DatasetProviderLimitationError,
    DatasetProviderUnavailableError,
    DatasetProviderUnsupportedScopeError,
    FixtureNewsProvider,
    HistoricalNewsProvider,
    ProviderFetchRequest,
    ProviderRawRecord,
)
from quantitative_sentiment_analysis.backtest_dataset.normalization import (
    NormalizedNewsRecord,
    ProviderNormalizationError,
    normalize_provider_records,
)
from quantitative_sentiment_analysis.backtest_dataset.orchestrator import (
    DEFAULT_DATASET_SEED,
    DatasetOrchestrator,
    metadata_for_preview,
)

__all__ = [
    "CompletedDatasetRepository",
    "CompletedDatasetRunIncompleteError",
    "CompletedDatasetRunNotFoundError",
    "CompletedDatasetRunUnsupportedError",
    "DatasetProviderConfigurationError",
    "DatasetProviderError",
    "DatasetProviderLimitationError",
    "DatasetProviderUnavailableError",
    "DatasetProviderUnsupportedScopeError",
    "DatasetOrchestrator",
    "DatasetProviderLimitation",
    "DatasetRunPreview",
    "DatasetRunStatus",
    "DatasetRunSummary",
    "FixtureNewsProvider",
    "HistoricalNewsProvider",
    "InMemoryCompletedDatasetRepository",
    "MAX_DATASET_PREVIEW_RECORDS",
    "DEFAULT_DATASET_SEED",
    "NormalizedNewsRecord",
    "ProviderFetchRequest",
    "ProviderNormalizationError",
    "ProviderRawRecord",
    "get_completed_dataset_repository",
    "metadata_for_preview",
    "normalize_provider_records",
]
