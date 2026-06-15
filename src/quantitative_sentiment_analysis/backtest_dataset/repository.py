from __future__ import annotations

from threading import Lock
from typing import Protocol

from quantitative_sentiment_analysis.backtest_dataset.schemas import (
    DatasetRunPreview,
    DatasetRunStatus,
    DatasetRunSummary,
)
from quantitative_sentiment_analysis.contracts import DatasetRecord, Instrument, RunMode


class CompletedDatasetRunNotFoundError(RuntimeError):
    """Raised when a local/dev completed dataset run is missing."""


class CompletedDatasetRunUnsupportedError(RuntimeError):
    """Raised when completed dataset storage receives an unsupported scope."""


class CompletedDatasetRunIncompleteError(RuntimeError):
    """Raised when completed-run storage receives a non-terminal state."""


class CompletedDatasetRepository(Protocol):
    """Repository boundary for local/dev deterministic BACKTEST dataset runs."""

    def save_run(
        self,
        summary: DatasetRunSummary,
        records: tuple[DatasetRecord, ...] | list[DatasetRecord],
    ) -> DatasetRunPreview:
        """Persist a completed or provider-limited dataset run for one workspace."""

    def get_run(self, workspace_id: str, run_id: str) -> DatasetRunPreview:
        """Return one stored dataset run by workspace and run ID."""


class InMemoryCompletedDatasetRepository:
    """Non-production, process-local storage for S-02 completed dataset runs."""

    storage_description = (
        "local/dev in-memory non-production completed deterministic BACKTEST "
        "dataset run storage"
    )

    def __init__(self) -> None:
        self._runs: dict[tuple[str, str], DatasetRunPreview] = {}
        self._lock = Lock()

    def save_run(
        self,
        summary: DatasetRunSummary,
        records: tuple[DatasetRecord, ...] | list[DatasetRecord],
    ) -> DatasetRunPreview:
        self._ensure_terminal_state(summary)
        preview = DatasetRunPreview(summary=summary, records=tuple(records))
        key = (summary.workspace_id, summary.run_id)
        with self._lock:
            self._runs[key] = preview
        return preview

    def get_run(self, workspace_id: str, run_id: str) -> DatasetRunPreview:
        with self._lock:
            preview = self._runs.get((workspace_id, run_id))
        if preview is None:
            raise CompletedDatasetRunNotFoundError(
                "local/dev in-memory non-production completed BACKTEST dataset "
                f"run was not found for workspace {workspace_id!r} and run {run_id!r}"
            )
        return preview

    def _ensure_terminal_state(self, summary: DatasetRunSummary) -> None:
        if summary.status in {
            DatasetRunStatus.DRAFT,
            DatasetRunStatus.RUNNING,
        }:
            raise CompletedDatasetRunIncompleteError(
                "local/dev completed dataset storage accepts only terminal "
                "COMPLETED or FAILED_PROVIDER_LIMITATION states"
            )
        if summary.mode is not RunMode.BACKTEST or summary.instrument is not Instrument.BTCUSD:
            raise CompletedDatasetRunUnsupportedError(
                "completed dataset storage supports only BTCUSD BACKTEST scope"
            )


_default_repository = InMemoryCompletedDatasetRepository()


def get_completed_dataset_repository() -> CompletedDatasetRepository:
    return _default_repository
