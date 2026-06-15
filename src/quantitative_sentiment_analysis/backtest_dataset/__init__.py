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
    "DatasetProviderLimitation",
    "DatasetRunPreview",
    "DatasetRunStatus",
    "DatasetRunSummary",
    "FixtureNewsProvider",
    "HistoricalNewsProvider",
    "InMemoryCompletedDatasetRepository",
    "MAX_DATASET_PREVIEW_RECORDS",
    "NormalizedNewsRecord",
    "ProviderFetchRequest",
    "ProviderNormalizationError",
    "ProviderRawRecord",
    "get_completed_dataset_repository",
    "normalize_provider_records",
]
