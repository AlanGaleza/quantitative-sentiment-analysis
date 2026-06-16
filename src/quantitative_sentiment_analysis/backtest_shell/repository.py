from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from threading import Lock
from typing import Annotated, Protocol
from urllib.parse import quote

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from quantitative_sentiment_analysis.backtest_shell.schemas import (
    BacktestRunShell,
    BacktestRunStatus,
    CreateBacktestRunRequest,
)
from quantitative_sentiment_analysis.contracts import Instrument, RunMode
from quantitative_sentiment_analysis.persistence.database import get_database_session
from quantitative_sentiment_analysis.persistence.models import (
    BacktestRunModel,
    WorkspaceModel,
)


class BacktestShellRunNotFoundError(RuntimeError):
    """Raised when a local workspace/run shell pair does not exist."""


class BacktestShellUnsupportedError(RuntimeError):
    """Raised when a draft shell is outside BTCUSD BACKTEST scope."""


class BacktestShellRepository(Protocol):
    """Repository boundary for local/dev BACKTEST run shells."""

    def create_draft_run(
        self,
        workspace_id: str,
        request: CreateBacktestRunRequest,
    ) -> BacktestRunShell:
        """Create a draft run shell for one workspace."""
        ...

    def get_run(self, workspace_id: str, run_id: str) -> BacktestRunShell:
        """Return one draft run shell by workspace and run ID."""
        ...


RunIdFactory = Callable[[str, CreateBacktestRunRequest], str]
Clock = Callable[[], datetime]


class InMemoryBacktestShellRepository:
    """Non-production, process-local storage for S-01 draft BACKTEST shells."""

    storage_description = (
        "local/dev in-memory non-production draft BACKTEST run shell storage"
    )

    def __init__(
        self,
        *,
        run_id_factory: RunIdFactory | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._runs: dict[tuple[str, str], BacktestRunShell] = {}
        self._lock = Lock()
        self._run_id_factory = run_id_factory or create_sequence_run_id_factory()
        self._clock = clock or (lambda: datetime.now(UTC))

    def create_draft_run(
        self,
        workspace_id: str,
        request: CreateBacktestRunRequest,
    ) -> BacktestRunShell:
        self._ensure_supported(request)
        run_id = self._run_id_factory(workspace_id, request)
        run = BacktestRunShell(
            workspace_id=workspace_id,
            run_id=run_id,
            instrument=request.instrument,
            mode=request.mode,
            timeframe_start=request.timeframe_start,
            timeframe_end=request.timeframe_end,
            status=BacktestRunStatus.DRAFT,
            created_at=self._clock(),
            quality_report_path=_quality_report_path(
                workspace_id=workspace_id,
                run_id=run_id,
            ),
        )
        with self._lock:
            self._runs[(workspace_id, run_id)] = run
        return run

    def get_run(self, workspace_id: str, run_id: str) -> BacktestRunShell:
        with self._lock:
            run = self._runs.get((workspace_id, run_id))
        if run is None:
            raise BacktestShellRunNotFoundError(
                "local/dev in-memory BACKTEST run shell was not found "
                f"for workspace {workspace_id!r} and run {run_id!r}"
            )
        return run

    def _ensure_supported(self, request: CreateBacktestRunRequest) -> None:
        if request.instrument is not Instrument.BTCUSD or request.mode is not RunMode.BACKTEST:
            raise BacktestShellUnsupportedError(
                "draft run shell supports only BTCUSD BACKTEST in local/dev mode"
            )


class PostgresBacktestShellRepository:
    """Postgres-backed storage for workspace-owned draft BACKTEST shells."""

    storage_description = "postgres durable draft BACKTEST run shell storage"

    def __init__(
        self,
        session: Session,
        *,
        run_id_factory: RunIdFactory | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._session = session
        self._run_id_factory = run_id_factory
        self._clock = clock or (lambda: datetime.now(UTC))

    def create_draft_run(
        self,
        workspace_id: str,
        request: CreateBacktestRunRequest,
    ) -> BacktestRunShell:
        return self._create_draft_run(
            workspace_id=workspace_id,
            request=request,
            config_id=None,
        )

    def create_draft_run_from_config(
        self,
        *,
        workspace_id: str,
        config_id: uuid.UUID,
        request: CreateBacktestRunRequest,
    ) -> BacktestRunShell:
        return self._create_draft_run(
            workspace_id=workspace_id,
            request=request,
            config_id=config_id,
        )

    def _create_draft_run(
        self,
        *,
        workspace_id: str,
        request: CreateBacktestRunRequest,
        config_id: uuid.UUID | None,
    ) -> BacktestRunShell:
        self._ensure_supported(request)
        workspace = self._get_workspace(workspace_id)
        if workspace is None:
            raise BacktestShellRunNotFoundError(
                f"workspace {workspace_id!r} was not found"
            )

        run_id = self._next_run_id(
            workspace=workspace,
            workspace_id=workspace_id,
            request=request,
        )
        run = BacktestRunModel(
            workspace_id=workspace.id,
            run_id=run_id,
            config_id=config_id,
            instrument=request.instrument.value,
            mode=request.mode.value,
            timeframe_start=request.timeframe_start,
            timeframe_end=request.timeframe_end,
            status=BacktestRunStatus.DRAFT.value,
            created_at=self._clock(),
        )
        self._session.add(run)
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise BacktestShellUnsupportedError(
                "draft run could not be stored with a unique workspace/run identity"
            ) from exc
        self._session.refresh(run)
        return _run_model_to_shell(run, workspace_slug=workspace.slug)

    def get_run(self, workspace_id: str, run_id: str) -> BacktestRunShell:
        row = self._session.execute(
            select(BacktestRunModel, WorkspaceModel.slug)
            .join(WorkspaceModel, BacktestRunModel.workspace_id == WorkspaceModel.id)
            .where(WorkspaceModel.slug == workspace_id, BacktestRunModel.run_id == run_id)
        ).one_or_none()
        if row is None:
            raise BacktestShellRunNotFoundError(
                "Postgres BACKTEST run shell was not found "
                f"for workspace {workspace_id!r} and run {run_id!r}"
            )
        run, workspace_slug = row
        return _run_model_to_shell(run, workspace_slug=workspace_slug)

    def _ensure_supported(self, request: CreateBacktestRunRequest) -> None:
        if request.instrument is not Instrument.BTCUSD or request.mode is not RunMode.BACKTEST:
            raise BacktestShellUnsupportedError(
                "draft run shell supports only BTCUSD BACKTEST"
            )

    def _get_workspace(self, workspace_id: str) -> WorkspaceModel | None:
        return self._session.scalar(
            select(WorkspaceModel).where(WorkspaceModel.slug == workspace_id)
        )

    def _next_run_id(
        self,
        *,
        workspace: WorkspaceModel,
        workspace_id: str,
        request: CreateBacktestRunRequest,
    ) -> str:
        if self._run_id_factory is not None:
            return self._run_id_factory(workspace_id, request)

        prefix = "draft-run"
        existing_run_ids = self._session.scalars(
            select(BacktestRunModel.run_id).where(
                BacktestRunModel.workspace_id == workspace.id,
                BacktestRunModel.run_id.like(f"{prefix}-%"),
            )
        )
        highest_sequence = 0
        for run_id in existing_run_ids:
            suffix = run_id.removeprefix(f"{prefix}-")
            if suffix.isdigit():
                highest_sequence = max(highest_sequence, int(suffix))
        return f"{prefix}-{highest_sequence + 1:06d}"


def create_sequence_run_id_factory(prefix: str = "draft-run") -> RunIdFactory:
    counter = 0
    lock = Lock()

    def next_run_id(
        workspace_id: str,
        request: CreateBacktestRunRequest,
    ) -> str:
        nonlocal counter
        with lock:
            counter += 1
            return f"{prefix}-{counter:06d}"

    return next_run_id


_default_repository = InMemoryBacktestShellRepository()


def get_backtest_shell_repository(
    session: Annotated[Session, Depends(get_database_session)],
) -> BacktestShellRepository:
    return PostgresBacktestShellRepository(session)


def _quality_report_path(*, workspace_id: str, run_id: str) -> str:
    return (
        f"/workspaces/{quote(workspace_id, safe='')}/backtests/"
        f"{quote(run_id, safe='')}/quality"
    )


def _run_model_to_shell(
    run: BacktestRunModel,
    *,
    workspace_slug: str,
) -> BacktestRunShell:
    return BacktestRunShell(
        workspace_id=workspace_slug,
        run_id=run.run_id,
        instrument=Instrument(run.instrument),
        mode=RunMode(run.mode),
        timeframe_start=run.timeframe_start,
        timeframe_end=run.timeframe_end,
        status=BacktestRunStatus(run.status),
        created_at=run.created_at,
        quality_report_path=_quality_report_path(
            workspace_id=workspace_slug,
            run_id=run.run_id,
        ),
    )
