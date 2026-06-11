from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from quantitative_sentiment_analysis.backtest_quality import (
    DirectionalBias,
    RelevanceLabel,
)
from quantitative_sentiment_analysis.backtest_quality.schemas import (
    QualityInputRecord,
    RealizedDirection,
)

BASE_TIME = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
WORKSPACE_ID = "workspace-alpha"
RUN_ID = "run-001"
MODEL_VERSION = "sentiment-rules-v1"
CONFIG_VERSION = "quality-config-v1"


def make_quality_record(
    index: int,
    *,
    sentiment_score: float,
    directional_bias: DirectionalBias,
    later_return: float | None,
    realized_direction: RealizedDirection | None,
    relevance: RelevanceLabel = RelevanceLabel.RELEVANT,
    workspace_id: str = WORKSPACE_ID,
    run_id: str = RUN_ID,
    model_version: str = MODEL_VERSION,
    config_version: str = CONFIG_VERSION,
) -> QualityInputRecord:
    return QualityInputRecord(
        workspace_id=workspace_id,
        run_id=run_id,
        record_id=f"record-{index:03d}",
        event_timestamp=BASE_TIME + timedelta(minutes=index),
        headline=f"BTCUSD quality fixture {index}",
        source_name="Example Crypto News",
        sentiment_score=sentiment_score,
        directional_bias=directional_bias,
        confidence=0.75,
        relevance=relevance,
        later_return=later_return,
        realized_direction=realized_direction,
        model_version=model_version,
        config_version=config_version,
    )


def quality_records(
    *,
    workspace_id: str = WORKSPACE_ID,
    run_id: str = RUN_ID,
) -> list[QualityInputRecord]:
    return [
        make_quality_record(
            1,
            sentiment_score=0.8,
            directional_bias=DirectionalBias.LONG,
            later_return=0.04,
            realized_direction=RealizedDirection.UP,
            workspace_id=workspace_id,
            run_id=run_id,
        ),
        make_quality_record(
            2,
            sentiment_score=-0.6,
            directional_bias=DirectionalBias.SHORT,
            later_return=-0.03,
            realized_direction=RealizedDirection.DOWN,
            workspace_id=workspace_id,
            run_id=run_id,
        ),
        make_quality_record(
            3,
            sentiment_score=0.0,
            directional_bias=DirectionalBias.FLAT,
            later_return=0.0,
            realized_direction=RealizedDirection.FLAT,
            workspace_id=workspace_id,
            run_id=run_id,
        ),
        make_quality_record(
            4,
            sentiment_score=0.5,
            directional_bias=DirectionalBias.LONG,
            later_return=None,
            realized_direction=None,
            workspace_id=workspace_id,
            run_id=run_id,
        ),
        make_quality_record(
            5,
            sentiment_score=-0.9,
            directional_bias=DirectionalBias.SHORT,
            later_return=-0.02,
            realized_direction=RealizedDirection.DOWN,
            relevance=RelevanceLabel.NOISE,
            workspace_id=workspace_id,
            run_id=run_id,
        ),
    ]


class FixtureQualityInputProvider:
    def get_quality_inputs(
        self,
        workspace_id: str,
        run_id: str,
    ) -> Sequence[QualityInputRecord]:
        return quality_records(workspace_id=workspace_id, run_id=run_id)
