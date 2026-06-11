from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
import os
from typing import Protocol

from quantitative_sentiment_analysis.backtest_quality.schemas import (
    DirectionalBias,
    QualityInputRecord,
    RealizedDirection,
    RelevanceLabel,
)

QSA_RUNTIME_ENV = "QSA_RUNTIME_ENV"
QSA_BACKTEST_QUALITY_PROVIDER = "QSA_BACKTEST_QUALITY_PROVIDER"
LOCAL_FIXTURE_PROVIDER = "local-fixture"


class QualityRunNotReadyError(RuntimeError):
    """Raised when real S-02 completed-run storage is not available yet."""


class QualityRunNotFoundError(RuntimeError):
    """Raised when a workspace/run pair does not exist."""


class QualityRunIncompleteError(RuntimeError):
    """Raised when a run exists but cannot be evaluated yet."""


class QualityRunUnsupportedError(RuntimeError):
    """Raised when a run is outside BTCUSD BACKTEST quality-view scope."""


class QualityInputProvider(Protocol):
    def get_quality_inputs(
        self,
        workspace_id: str,
        run_id: str,
    ) -> Sequence[QualityInputRecord]:
        """Return deterministic quality inputs for one completed BACKTEST run."""


class NotReadyQualityInputProvider:
    def __init__(
        self,
        message: str = "S-02 deterministic completed-run storage is not integrated yet",
    ) -> None:
        self.message = message

    def get_quality_inputs(
        self,
        workspace_id: str,
        run_id: str,
    ) -> Sequence[QualityInputRecord]:
        raise QualityRunNotReadyError(self.message)


class LocalFixtureQualityInputProvider:
    def get_quality_inputs(
        self,
        workspace_id: str,
        run_id: str,
    ) -> Sequence[QualityInputRecord]:
        return _local_fixture_records(workspace_id=workspace_id, run_id=run_id)


def get_quality_input_provider() -> QualityInputProvider:
    configured_provider = os.getenv(QSA_BACKTEST_QUALITY_PROVIDER, "").strip()
    if configured_provider == LOCAL_FIXTURE_PROVIDER:
        if os.getenv(QSA_RUNTIME_ENV, "").strip() != "local":
            return NotReadyQualityInputProvider(
                "local fixture quality provider requires QSA_RUNTIME_ENV=local"
            )
        return LocalFixtureQualityInputProvider()

    if configured_provider:
        return NotReadyQualityInputProvider(
            f"quality input provider {configured_provider!r} is not available"
        )

    return NotReadyQualityInputProvider()


def _local_fixture_records(
    *,
    workspace_id: str,
    run_id: str,
) -> list[QualityInputRecord]:
    base_time = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)

    return [
        _local_fixture_record(
            1,
            base_time=base_time,
            workspace_id=workspace_id,
            run_id=run_id,
            sentiment_score=0.8,
            directional_bias=DirectionalBias.LONG,
            later_return=0.04,
            realized_direction=RealizedDirection.UP,
        ),
        _local_fixture_record(
            2,
            base_time=base_time,
            workspace_id=workspace_id,
            run_id=run_id,
            sentiment_score=-0.6,
            directional_bias=DirectionalBias.SHORT,
            later_return=-0.03,
            realized_direction=RealizedDirection.DOWN,
        ),
        _local_fixture_record(
            3,
            base_time=base_time,
            workspace_id=workspace_id,
            run_id=run_id,
            sentiment_score=0.0,
            directional_bias=DirectionalBias.FLAT,
            later_return=0.0,
            realized_direction=RealizedDirection.FLAT,
        ),
        _local_fixture_record(
            4,
            base_time=base_time,
            workspace_id=workspace_id,
            run_id=run_id,
            sentiment_score=0.5,
            directional_bias=DirectionalBias.LONG,
            later_return=None,
            realized_direction=None,
        ),
        _local_fixture_record(
            5,
            base_time=base_time,
            workspace_id=workspace_id,
            run_id=run_id,
            sentiment_score=-0.9,
            directional_bias=DirectionalBias.SHORT,
            later_return=-0.02,
            realized_direction=RealizedDirection.DOWN,
            relevance=RelevanceLabel.NOISE,
        ),
    ]


def _local_fixture_record(
    index: int,
    *,
    base_time: datetime,
    workspace_id: str,
    run_id: str,
    sentiment_score: float,
    directional_bias: DirectionalBias,
    later_return: float | None,
    realized_direction: RealizedDirection | None,
    relevance: RelevanceLabel = RelevanceLabel.RELEVANT,
) -> QualityInputRecord:
    return QualityInputRecord(
        workspace_id=workspace_id,
        run_id=run_id,
        record_id=f"local-fixture-record-{index:03d}",
        event_timestamp=base_time + timedelta(minutes=index),
        headline=f"BTCUSD local quality fixture {index}",
        source_name="Local Fixture News",
        sentiment_score=sentiment_score,
        directional_bias=directional_bias,
        confidence=0.75,
        relevance=relevance,
        later_return=later_return,
        realized_direction=realized_direction,
        model_version="sentiment-rules-v1-local-fixture",
        config_version="quality-config-v1-local-fixture",
    )
