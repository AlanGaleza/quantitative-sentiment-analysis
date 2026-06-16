from __future__ import annotations

import uuid
from threading import Lock
from typing import Annotated, Protocol

from fastapi import Depends
from sqlalchemy import delete, nulls_first, select
from sqlalchemy.orm import Session

from quantitative_sentiment_analysis.backtest_dataset.schemas import (
    DatasetProviderLimitation,
)
from quantitative_sentiment_analysis.backtest_dataset.schemas import (
    MAX_DATASET_PREVIEW_RECORDS,
    DatasetRunPreview,
    DatasetRunStatus,
    DatasetRunSummary,
)
from quantitative_sentiment_analysis.contracts import (
    DatasetRecord,
    DirectionalBias,
    Instrument,
    RelevanceLabel,
    RunMode,
)
from quantitative_sentiment_analysis.persistence.database import get_database_session
from quantitative_sentiment_analysis.persistence.models import (
    BacktestRunModel,
    DatasetRecordModel,
    DatasetRunModel,
    WorkspaceModel,
)


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
        ...

    def get_run(self, workspace_id: str, run_id: str) -> DatasetRunPreview:
        """Return one stored dataset run by workspace and run ID."""
        ...

    def list_records(
        self,
        workspace_id: str,
        run_id: str,
    ) -> tuple[DatasetRecord, ...]:
        """Return all stored records for one completed dataset run."""
        ...


class InMemoryCompletedDatasetRepository:
    """Non-production, process-local storage for S-02 completed dataset runs."""

    storage_description = (
        "local/dev in-memory non-production completed deterministic BACKTEST "
        "dataset run storage"
    )

    def __init__(self) -> None:
        self._runs: dict[tuple[str, str], DatasetRunPreview] = {}
        self._records: dict[tuple[str, str], tuple[DatasetRecord, ...]] = {}
        self._lock = Lock()

    def save_run(
        self,
        summary: DatasetRunSummary,
        records: tuple[DatasetRecord, ...] | list[DatasetRecord],
    ) -> DatasetRunPreview:
        _ensure_terminal_state(summary)
        stored_records = tuple(records)
        _ensure_records_match_summary(summary, stored_records)
        preview = DatasetRunPreview(
            summary=summary,
            records=stored_records[:MAX_DATASET_PREVIEW_RECORDS],
        )
        key = (summary.workspace_id, summary.run_id)
        with self._lock:
            self._runs[key] = preview
            self._records[key] = stored_records
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

    def list_records(
        self,
        workspace_id: str,
        run_id: str,
    ) -> tuple[DatasetRecord, ...]:
        with self._lock:
            records = self._records.get((workspace_id, run_id))
        if records is None:
            raise CompletedDatasetRunNotFoundError(
                "local/dev in-memory non-production completed BACKTEST dataset "
                f"records were not found for workspace {workspace_id!r} and run {run_id!r}"
            )
        return records


class PostgresCompletedDatasetRepository:
    """Postgres-backed storage for completed deterministic BACKTEST datasets."""

    storage_description = "postgres durable completed deterministic BACKTEST dataset storage"

    def __init__(self, session: Session) -> None:
        self._session = session

    def save_run(
        self,
        summary: DatasetRunSummary,
        records: tuple[DatasetRecord, ...] | list[DatasetRecord],
    ) -> DatasetRunPreview:
        _ensure_terminal_state(summary)
        stored_records = tuple(records)
        _ensure_records_match_summary(summary, stored_records)
        backtest_run = self._get_backtest_run(summary.workspace_id, summary.run_id)
        if backtest_run is None:
            raise CompletedDatasetRunNotFoundError(
                "Postgres draft BACKTEST run was not found "
                f"for workspace {summary.workspace_id!r} and run {summary.run_id!r}"
            )

        try:
            self._delete_existing_dataset(backtest_run.workspace_id, summary.run_id)
            dataset_run = DatasetRunModel(
                workspace_id=backtest_run.workspace_id,
                run_id=summary.run_id,
                instrument=summary.instrument.value,
                mode=summary.mode.value,
                timeframe_start=summary.timeframe_start,
                timeframe_end=summary.timeframe_end,
                status=summary.status.value,
                provider_name=summary.provider_name,
                record_count=summary.record_count,
                relevant_count=summary.relevant_count,
                noise_count=summary.noise_count,
                irrelevant_count=summary.irrelevant_count,
                model_version=summary.model_version,
                config_version=summary.config_version,
                input_fingerprint=summary.input_fingerprint,
                provider_limitation_provider_name=(
                    summary.provider_limitation.provider_name
                    if summary.provider_limitation
                    else None
                ),
                provider_limitation_reason=(
                    summary.provider_limitation.reason
                    if summary.provider_limitation
                    else None
                ),
                provider_limitation_detail=(
                    summary.provider_limitation.detail
                    if summary.provider_limitation
                    else None
                ),
            )
            self._session.add(dataset_run)
            self._session.flush()
            self._session.add_all(
                _record_to_model(
                    record,
                    workspace_uuid=backtest_run.workspace_id,
                )
                for record in stored_records
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        return self.get_run(summary.workspace_id, summary.run_id)

    def get_run(self, workspace_id: str, run_id: str) -> DatasetRunPreview:
        workspace = self._get_workspace(workspace_id)
        if workspace is None:
            raise CompletedDatasetRunNotFoundError(
                f"Postgres workspace {workspace_id!r} was not found"
            )
        dataset_run = self._session.scalar(
            select(DatasetRunModel).where(
                DatasetRunModel.workspace_id == workspace.id,
                DatasetRunModel.run_id == run_id,
            )
        )
        if dataset_run is None:
            raise CompletedDatasetRunNotFoundError(
                "Postgres completed BACKTEST dataset run was not found "
                f"for workspace {workspace_id!r} and run {run_id!r}"
            )
        records = self.list_records(workspace_id, run_id)
        return DatasetRunPreview(
            summary=_summary_from_model(dataset_run, workspace_slug=workspace.slug),
            records=records[:MAX_DATASET_PREVIEW_RECORDS],
        )

    def list_records(
        self,
        workspace_id: str,
        run_id: str,
    ) -> tuple[DatasetRecord, ...]:
        workspace = self._get_workspace(workspace_id)
        if workspace is None:
            raise CompletedDatasetRunNotFoundError(
                f"Postgres workspace {workspace_id!r} was not found"
            )
        dataset_run_exists = self._session.scalar(
            select(DatasetRunModel.id).where(
                DatasetRunModel.workspace_id == workspace.id,
                DatasetRunModel.run_id == run_id,
            )
        )
        if dataset_run_exists is None:
            raise CompletedDatasetRunNotFoundError(
                "Postgres completed BACKTEST dataset records were not found "
                f"for workspace {workspace_id!r} and run {run_id!r}"
            )

        rows = self._session.scalars(
            select(DatasetRecordModel)
            .where(
                DatasetRecordModel.workspace_id == workspace.id,
                DatasetRecordModel.run_id == run_id,
            )
            .order_by(
                DatasetRecordModel.timestamp,
                nulls_first(DatasetRecordModel.record_id),
                nulls_first(DatasetRecordModel.source_id),
                nulls_first(DatasetRecordModel.source_name),
                DatasetRecordModel.headline,
            )
        )
        return tuple(
            _record_from_model(record, workspace_slug=workspace.slug) for record in rows
        )

    def _delete_existing_dataset(self, workspace_uuid: uuid.UUID, run_id: str) -> None:
        self._session.execute(
            delete(DatasetRecordModel).where(
                DatasetRecordModel.workspace_id == workspace_uuid,
                DatasetRecordModel.run_id == run_id,
            )
        )
        self._session.execute(
            delete(DatasetRunModel).where(
                DatasetRunModel.workspace_id == workspace_uuid,
                DatasetRunModel.run_id == run_id,
            )
        )
        self._session.flush()

    def _get_backtest_run(
        self,
        workspace_id: str,
        run_id: str,
    ) -> BacktestRunModel | None:
        return self._session.scalar(
            select(BacktestRunModel)
            .join(WorkspaceModel, BacktestRunModel.workspace_id == WorkspaceModel.id)
            .where(WorkspaceModel.slug == workspace_id, BacktestRunModel.run_id == run_id)
        )

    def _get_workspace(self, workspace_id: str) -> WorkspaceModel | None:
        return self._session.scalar(
            select(WorkspaceModel).where(WorkspaceModel.slug == workspace_id)
        )


_default_repository = InMemoryCompletedDatasetRepository()


def get_completed_dataset_repository(
    session: Annotated[Session, Depends(get_database_session)],
) -> CompletedDatasetRepository:
    return PostgresCompletedDatasetRepository(session)


def _ensure_terminal_state(summary: DatasetRunSummary) -> None:
    if summary.status in {
        DatasetRunStatus.DRAFT,
        DatasetRunStatus.RUNNING,
    }:
        raise CompletedDatasetRunIncompleteError(
            "completed dataset storage accepts only terminal "
            "COMPLETED or FAILED_PROVIDER_LIMITATION states"
        )
    if summary.mode is not RunMode.BACKTEST or summary.instrument is not Instrument.BTCUSD:
        raise CompletedDatasetRunUnsupportedError(
            "completed dataset storage supports only BTCUSD BACKTEST scope"
        )


def _ensure_records_match_summary(
    summary: DatasetRunSummary,
    records: tuple[DatasetRecord, ...],
) -> None:
    if len(records) != summary.record_count:
        raise ValueError("stored record_count must match summary record_count")

    relevance_counts = {
        RelevanceLabel.RELEVANT: 0,
        RelevanceLabel.NOISE: 0,
        RelevanceLabel.IRRELEVANT: 0,
    }
    for record in records:
        if record.workspace_id != summary.workspace_id:
            raise ValueError("stored record workspace_id must match summary")
        if record.run_id != summary.run_id:
            raise ValueError("stored record run_id must match summary")
        if record.instrument is not summary.instrument:
            raise ValueError("stored record instrument must match summary")
        if record.mode is not summary.mode:
            raise ValueError("stored record mode must match summary")
        if record.model_version != summary.model_version:
            raise ValueError("stored record model_version must match summary")
        if record.config_version != summary.config_version:
            raise ValueError("stored record config_version must match summary")
        relevance_counts[record.relevance] += 1

    if relevance_counts[RelevanceLabel.RELEVANT] != summary.relevant_count:
        raise ValueError("stored relevant_count must match summary relevant_count")
    if relevance_counts[RelevanceLabel.NOISE] != summary.noise_count:
        raise ValueError("stored noise_count must match summary noise_count")
    if relevance_counts[RelevanceLabel.IRRELEVANT] != summary.irrelevant_count:
        raise ValueError("stored irrelevant_count must match summary irrelevant_count")
    if summary.status is DatasetRunStatus.FAILED_PROVIDER_LIMITATION and records:
        raise ValueError("provider-limited dataset runs must not store records")


def _summary_from_model(
    dataset_run: DatasetRunModel,
    *,
    workspace_slug: str,
) -> DatasetRunSummary:
    provider_limitation = None
    if dataset_run.provider_limitation_reason is not None:
        provider_limitation = DatasetProviderLimitation(
            provider_name=(
                dataset_run.provider_limitation_provider_name
                or dataset_run.provider_name
            ),
            reason=dataset_run.provider_limitation_reason,
            detail=dataset_run.provider_limitation_detail,
        )
    return DatasetRunSummary(
        workspace_id=workspace_slug,
        run_id=dataset_run.run_id,
        instrument=Instrument(dataset_run.instrument),
        mode=RunMode(dataset_run.mode),
        timeframe_start=dataset_run.timeframe_start,
        timeframe_end=dataset_run.timeframe_end,
        status=DatasetRunStatus(dataset_run.status),
        provider_name=dataset_run.provider_name,
        record_count=dataset_run.record_count,
        relevant_count=dataset_run.relevant_count,
        noise_count=dataset_run.noise_count,
        irrelevant_count=dataset_run.irrelevant_count,
        model_version=dataset_run.model_version,
        config_version=dataset_run.config_version,
        input_fingerprint=dataset_run.input_fingerprint,
        provider_limitation=provider_limitation,
    )


def _record_to_model(
    record: DatasetRecord,
    *,
    workspace_uuid: uuid.UUID,
) -> DatasetRecordModel:
    return DatasetRecordModel(
        workspace_id=workspace_uuid,
        run_id=record.run_id,
        record_id=record.record_id,
        timestamp=record.timestamp,
        headline=record.headline,
        source_id=record.source_id,
        source_name=record.source_name,
        instrument=record.instrument.value,
        mode=record.mode.value,
        sentiment_score=record.sentiment_score,
        directional_bias=record.directional_bias.value,
        confidence=record.confidence,
        relevance=record.relevance.value,
        model_version=record.model_version,
        config_version=record.config_version,
    )


def _record_from_model(
    record: DatasetRecordModel,
    *,
    workspace_slug: str,
) -> DatasetRecord:
    return DatasetRecord(
        workspace_id=workspace_slug,
        run_id=record.run_id,
        record_id=record.record_id,
        timestamp=record.timestamp,
        headline=record.headline,
        source_id=record.source_id,
        source_name=record.source_name,
        instrument=Instrument(record.instrument),
        mode=RunMode(record.mode),
        sentiment_score=record.sentiment_score,
        directional_bias=DirectionalBias(record.directional_bias),
        confidence=record.confidence,
        relevance=RelevanceLabel(record.relevance),
        model_version=record.model_version,
        config_version=record.config_version,
    )
