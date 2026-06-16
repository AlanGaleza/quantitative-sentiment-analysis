from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from quantitative_sentiment_analysis.backtest_configs.schemas import (
    BacktestConfigDetail,
    BacktestConfigListItem,
    CreateBacktestConfigRequest,
    UpdateBacktestConfigRequest,
)
from quantitative_sentiment_analysis.backtest_shell.repository import (
    PostgresBacktestShellRepository,
)
from quantitative_sentiment_analysis.backtest_shell.schemas import (
    BacktestRunShell,
    CreateBacktestRunRequest,
)
from quantitative_sentiment_analysis.contracts import Instrument, RunMode
from quantitative_sentiment_analysis.persistence.database import get_database_session
from quantitative_sentiment_analysis.persistence.models import (
    BacktestConfigModel,
    WorkspaceModel,
)


class BacktestConfigNotFoundError(RuntimeError):
    """Raised when a saved BACKTEST config is missing in the owned workspace."""


class BacktestConfigConflictError(RuntimeError):
    """Raised when a saved BACKTEST config violates a workspace uniqueness rule."""


class BacktestConfigRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        workspace_id: str,
        request: CreateBacktestConfigRequest,
    ) -> BacktestConfigDetail:
        workspace = self._require_workspace(workspace_id)
        config = BacktestConfigModel(
            workspace_id=workspace.id,
            name=request.name,
            instrument=request.instrument.value,
            mode=request.mode.value,
            timeframe_start=request.timeframe_start,
            timeframe_end=request.timeframe_end,
        )
        self._session.add(config)
        self._commit_or_conflict()
        self._session.refresh(config)
        return _config_detail(config, workspace_slug=workspace.slug)

    def list(self, workspace_id: str) -> tuple[BacktestConfigListItem, ...]:
        workspace = self._require_workspace(workspace_id)
        configs = self._session.scalars(
            select(BacktestConfigModel)
            .where(BacktestConfigModel.workspace_id == workspace.id)
            .order_by(BacktestConfigModel.updated_at.desc(), BacktestConfigModel.name)
        )
        return tuple(
            _config_list_item(config, workspace_slug=workspace.slug)
            for config in configs
        )

    def get(self, workspace_id: str, config_id: str) -> BacktestConfigDetail:
        workspace = self._require_workspace(workspace_id)
        config = self._get_config(workspace, config_id)
        if config is None:
            raise BacktestConfigNotFoundError(
                "saved BACKTEST config was not found"
            )
        return _config_detail(config, workspace_slug=workspace.slug)

    def update(
        self,
        workspace_id: str,
        config_id: str,
        request: UpdateBacktestConfigRequest,
    ) -> BacktestConfigDetail:
        workspace = self._require_workspace(workspace_id)
        config = self._get_config(workspace, config_id)
        if config is None:
            raise BacktestConfigNotFoundError(
                "saved BACKTEST config was not found"
            )

        name = request.name if request.name is not None else config.name
        instrument = request.instrument or Instrument(config.instrument)
        mode = request.mode or RunMode(config.mode)
        timeframe_start = request.timeframe_start or config.timeframe_start
        timeframe_end = request.timeframe_end or config.timeframe_end
        CreateBacktestRunRequest(
            instrument=instrument,
            mode=mode,
            timeframe_start=timeframe_start,
            timeframe_end=timeframe_end,
        )

        config.name = name
        config.instrument = instrument.value
        config.mode = mode.value
        config.timeframe_start = timeframe_start
        config.timeframe_end = timeframe_end
        config.updated_at = datetime.now(UTC)
        self._commit_or_conflict()
        self._session.refresh(config)
        return _config_detail(config, workspace_slug=workspace.slug)

    def delete(self, workspace_id: str, config_id: str) -> None:
        workspace = self._require_workspace(workspace_id)
        config = self._get_config(workspace, config_id)
        if config is None:
            raise BacktestConfigNotFoundError(
                "saved BACKTEST config was not found"
            )
        self._session.delete(config)
        self._session.commit()

    def create_draft_from_config(
        self,
        workspace_id: str,
        config_id: str,
    ) -> BacktestRunShell:
        workspace = self._require_workspace(workspace_id)
        config = self._get_config(workspace, config_id)
        if config is None:
            raise BacktestConfigNotFoundError(
                "saved BACKTEST config was not found"
            )
        return PostgresBacktestShellRepository(self._session).create_draft_run_from_config(
            workspace_id=workspace.slug,
            config_id=config.id,
            request=CreateBacktestRunRequest(
                instrument=Instrument(config.instrument),
                mode=RunMode(config.mode),
                timeframe_start=config.timeframe_start,
                timeframe_end=config.timeframe_end,
            ),
        )

    def _require_workspace(self, workspace_id: str) -> WorkspaceModel:
        workspace = self._session.scalar(
            select(WorkspaceModel).where(WorkspaceModel.slug == workspace_id)
        )
        if workspace is None:
            raise BacktestConfigNotFoundError(f"workspace {workspace_id!r} was not found")
        return workspace

    def _get_config(
        self,
        workspace: WorkspaceModel,
        config_id: str,
    ) -> BacktestConfigModel | None:
        parsed_id = _parse_uuid(config_id)
        if parsed_id is None:
            return None
        return self._session.scalar(
            select(BacktestConfigModel).where(
                BacktestConfigModel.workspace_id == workspace.id,
                BacktestConfigModel.id == parsed_id,
            )
        )

    def _commit_or_conflict(self) -> None:
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise BacktestConfigConflictError(
                "saved BACKTEST config name must be unique within the workspace"
            ) from exc


def get_backtest_config_repository(
    session: Annotated[Session, Depends(get_database_session)],
) -> BacktestConfigRepository:
    return BacktestConfigRepository(session)


def _config_detail(
    config: BacktestConfigModel,
    *,
    workspace_slug: str,
) -> BacktestConfigDetail:
    return BacktestConfigDetail.model_validate(
        _config_payload(config, workspace_slug=workspace_slug)
    )


def _config_list_item(
    config: BacktestConfigModel,
    *,
    workspace_slug: str,
) -> BacktestConfigListItem:
    return BacktestConfigListItem.model_validate(
        _config_payload(config, workspace_slug=workspace_slug)
    )


def _config_payload(
    config: BacktestConfigModel,
    *,
    workspace_slug: str,
) -> dict[str, object]:
    return {
        "id": str(config.id),
        "workspace_id": workspace_slug,
        "name": config.name,
        "instrument": config.instrument,
        "mode": config.mode,
        "timeframe_start": config.timeframe_start,
        "timeframe_end": config.timeframe_end,
        "created_at": config.created_at,
        "updated_at": config.updated_at,
    }


def _parse_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except ValueError:
        return None
