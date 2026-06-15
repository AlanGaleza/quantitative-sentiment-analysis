from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from threading import Lock
from typing import Protocol
from urllib.parse import quote

from quantitative_sentiment_analysis.backtest_shell.schemas import (
    BacktestRunShell,
    BacktestRunStatus,
    CreateBacktestRunRequest,
)
from quantitative_sentiment_analysis.contracts import Instrument, RunMode


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


def get_backtest_shell_repository() -> BacktestShellRepository:
    return _default_repository


def _quality_report_path(*, workspace_id: str, run_id: str) -> str:
    return (
        f"/workspaces/{quote(workspace_id, safe='')}/backtests/"
        f"{quote(run_id, safe='')}/quality"
    )
