from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from quantitative_sentiment_analysis.contracts import (
    DatasetRecord,
    Instrument,
    RelevanceLabel,
    RunMode,
)
from quantitative_sentiment_analysis.contracts.schemas import require_aware_datetime

MAX_DATASET_PREVIEW_RECORDS = 100


class DatasetRunStatus(StrEnum):
    DRAFT = "DRAFT"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED_PROVIDER_LIMITATION = "FAILED_PROVIDER_LIMITATION"


class DatasetProviderLimitation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_name: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    detail: str | None = None


class DatasetRunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    instrument: Instrument = Instrument.BTCUSD
    mode: RunMode = RunMode.BACKTEST
    timeframe_start: datetime
    timeframe_end: datetime
    status: DatasetRunStatus
    provider_name: str = Field(min_length=1)
    record_count: int = Field(ge=0)
    relevant_count: int = Field(ge=0)
    noise_count: int = Field(ge=0)
    irrelevant_count: int = Field(ge=0)
    model_version: str = Field(min_length=1)
    config_version: str = Field(min_length=1)
    input_fingerprint: str = Field(min_length=1)
    provider_limitation: DatasetProviderLimitation | None = None

    @field_validator("timeframe_start", "timeframe_end")
    @classmethod
    def timestamps_must_be_aware(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)

    @model_validator(mode="after")
    def must_be_btcusd_backtest_with_consistent_counts(self) -> Self:
        if self.instrument is not Instrument.BTCUSD:
            raise ValueError("instrument must be BTCUSD")
        if self.mode is not RunMode.BACKTEST:
            raise ValueError("mode must be BACKTEST")
        if self.timeframe_end < self.timeframe_start:
            raise ValueError("timeframe_end must be greater than or equal to timeframe_start")

        relevance_total = self.relevant_count + self.noise_count + self.irrelevant_count
        if self.record_count != relevance_total:
            raise ValueError(
                "record_count must equal relevant_count + noise_count + irrelevant_count"
            )

        if (
            self.status is DatasetRunStatus.FAILED_PROVIDER_LIMITATION
            and self.provider_limitation is None
        ):
            raise ValueError(
                "provider_limitation is required for FAILED_PROVIDER_LIMITATION"
            )
        if (
            self.status is DatasetRunStatus.COMPLETED
            and self.provider_limitation is not None
        ):
            raise ValueError("provider_limitation must be absent for COMPLETED runs")
        return self


class DatasetRunPreview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: DatasetRunSummary
    records: tuple[DatasetRecord, ...] = Field(
        default_factory=tuple,
        max_length=MAX_DATASET_PREVIEW_RECORDS,
    )

    @field_validator("records", mode="before")
    @classmethod
    def records_are_immutable_preview(
        cls,
        value: tuple[DatasetRecord, ...] | list[DatasetRecord],
    ) -> tuple[DatasetRecord, ...] | list[DatasetRecord]:
        return tuple(value)

    @model_validator(mode="after")
    def records_must_match_summary(self) -> Self:
        relevance_counts = {
            RelevanceLabel.RELEVANT: 0,
            RelevanceLabel.NOISE: 0,
            RelevanceLabel.IRRELEVANT: 0,
        }
        for record in self.records:
            if record.workspace_id != self.summary.workspace_id:
                raise ValueError("preview record workspace_id must match summary")
            if record.run_id != self.summary.run_id:
                raise ValueError("preview record run_id must match summary")
            if record.instrument is not self.summary.instrument:
                raise ValueError("preview record instrument must match summary")
            if record.mode is not self.summary.mode:
                raise ValueError("preview record mode must match summary")
            if record.model_version != self.summary.model_version:
                raise ValueError("preview record model_version must match summary")
            if record.config_version != self.summary.config_version:
                raise ValueError("preview record config_version must match summary")
            relevance_counts[record.relevance] += 1

        if self.summary.status is DatasetRunStatus.COMPLETED:
            if self.summary.record_count != len(self.records):
                raise ValueError("completed summary record_count must match preview records")
            if self.summary.relevant_count != relevance_counts[RelevanceLabel.RELEVANT]:
                raise ValueError("completed summary relevant_count must match records")
            if self.summary.noise_count != relevance_counts[RelevanceLabel.NOISE]:
                raise ValueError("completed summary noise_count must match records")
            if self.summary.irrelevant_count != relevance_counts[RelevanceLabel.IRRELEVANT]:
                raise ValueError("completed summary irrelevant_count must match records")
        return self
