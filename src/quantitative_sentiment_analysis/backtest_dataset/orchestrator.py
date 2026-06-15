from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from quantitative_sentiment_analysis.backtest_dataset.normalization import (
    NormalizedNewsRecord,
    normalize_provider_records,
)
from quantitative_sentiment_analysis.backtest_dataset.provider import (
    DatasetProviderConfigurationError,
    DatasetProviderLimitationError,
    DatasetProviderUnavailableError,
    HistoricalNewsProvider,
    ProviderFetchRequest,
)
from quantitative_sentiment_analysis.backtest_dataset.repository import (
    CompletedDatasetRepository,
)
from quantitative_sentiment_analysis.backtest_dataset.schemas import (
    DatasetRunPreview,
    DatasetRunStatus,
    DatasetRunSummary,
)
from quantitative_sentiment_analysis.backtest_shell import BacktestShellRepository
from quantitative_sentiment_analysis.contracts import (
    BacktestRunMetadata,
    DatasetRecord,
    RelevanceLabel,
    stable_json_dumps,
)
from quantitative_sentiment_analysis.sentiment_policy import (
    DEFAULT_POLICY_CONFIG,
    SentimentPolicyConfig,
    classification_confidence,
    directional_bias_for_score,
    relevance_for_text,
    score_text,
)

DEFAULT_DATASET_SEED = 42


@dataclass(frozen=True)
class DatasetOrchestrator:
    shell_repository: BacktestShellRepository
    completed_repository: CompletedDatasetRepository
    provider: HistoricalNewsProvider
    policy_config: SentimentPolicyConfig = DEFAULT_POLICY_CONFIG
    seed: int = DEFAULT_DATASET_SEED

    def run_dataset(
        self,
        *,
        workspace_id: str,
        run_id: str,
    ) -> DatasetRunPreview:
        draft_run = self.shell_repository.get_run(workspace_id, run_id)
        request = ProviderFetchRequest(
            workspace_id=draft_run.workspace_id,
            run_id=draft_run.run_id,
            instrument=draft_run.instrument,
            mode=draft_run.mode,
            timeframe_start=draft_run.timeframe_start,
            timeframe_end=draft_run.timeframe_end,
        )

        try:
            raw_records = self.provider.fetch_historical_news(request)
        except DatasetProviderLimitationError as exc:
            return self._save_provider_limitation(request=request, limitation_error=exc)
        except DatasetProviderConfigurationError as exc:
            limitation = DatasetProviderLimitationError(
                provider_name=self.provider.provider_name,
                reason="missing provider configuration",
                detail=str(exc),
            )
            return self._save_provider_limitation(
                request=request,
                limitation_error=limitation,
            )
        except DatasetProviderUnavailableError as exc:
            limitation = DatasetProviderLimitationError(
                provider_name=self.provider.provider_name,
                reason="provider unavailable",
                detail=str(exc),
            )
            return self._save_provider_limitation(
                request=request,
                limitation_error=limitation,
            )

        normalized_records = normalize_provider_records(
            provider_name=self.provider.provider_name,
            raw_records=raw_records,
        )
        input_fingerprint = _input_fingerprint(
            request=request,
            normalized_records=normalized_records,
            model_version=self.policy_config.model_version,
            config_version=self.policy_config.config_version,
            seed=self.seed,
        )
        records = tuple(
            self._dataset_record(
                request=request,
                normalized_record=normalized_record,
                deterministic_index=deterministic_index,
                input_fingerprint=input_fingerprint,
            )
            for deterministic_index, normalized_record in enumerate(normalized_records)
        )
        summary = _summary_for_records(
            request=request,
            provider_name=self.provider.provider_name,
            records=records,
            model_version=self.policy_config.model_version,
            config_version=self.policy_config.config_version,
            input_fingerprint=input_fingerprint,
        )
        return self.completed_repository.save_run(summary, records)

    def _dataset_record(
        self,
        *,
        request: ProviderFetchRequest,
        normalized_record: NormalizedNewsRecord,
        deterministic_index: int,
        input_fingerprint: str,
    ) -> DatasetRecord:
        relevance = relevance_for_text(
            normalized_record.headline,
            normalized_record.body,
            source_id=normalized_record.source_id,
            source_name=normalized_record.source_name,
        )
        sentiment_score = score_text(normalized_record.headline, normalized_record.body)
        if relevance is not RelevanceLabel.RELEVANT:
            sentiment_score = 0.0
        directional_bias = directional_bias_for_score(sentiment_score)
        confidence = classification_confidence(
            sentiment_score,
            relevance,
            headline=normalized_record.headline,
            source_id=normalized_record.source_id,
            source_name=normalized_record.source_name,
        )
        return DatasetRecord(
            workspace_id=request.workspace_id,
            run_id=request.run_id,
            record_id=_record_id(
                provider_name=normalized_record.provider_name,
                normalized_record=normalized_record,
                deterministic_index=deterministic_index,
                input_fingerprint=input_fingerprint,
            ),
            timestamp=normalized_record.timestamp,
            headline=normalized_record.headline,
            source_id=normalized_record.source_id,
            source_name=normalized_record.source_name or normalized_record.provider_name,
            instrument=request.instrument,
            mode=request.mode,
            sentiment_score=sentiment_score,
            directional_bias=directional_bias,
            confidence=confidence,
            relevance=relevance,
            model_version=self.policy_config.model_version,
            config_version=self.policy_config.config_version,
        )

    def _save_provider_limitation(
        self,
        *,
        request: ProviderFetchRequest,
        limitation_error: DatasetProviderLimitationError,
    ) -> DatasetRunPreview:
        summary = DatasetRunSummary(
            workspace_id=request.workspace_id,
            run_id=request.run_id,
            instrument=request.instrument,
            mode=request.mode,
            timeframe_start=request.timeframe_start,
            timeframe_end=request.timeframe_end,
            status=DatasetRunStatus.FAILED_PROVIDER_LIMITATION,
            provider_name=limitation_error.provider_name,
            record_count=0,
            relevant_count=0,
            noise_count=0,
            irrelevant_count=0,
            model_version=self.policy_config.model_version,
            config_version=self.policy_config.config_version,
            input_fingerprint=_provider_limitation_fingerprint(
                request=request,
                provider_name=limitation_error.provider_name,
                reason=limitation_error.reason,
                model_version=self.policy_config.model_version,
                config_version=self.policy_config.config_version,
                seed=self.seed,
            ),
            provider_limitation=limitation_error.to_schema(),
        )
        return self.completed_repository.save_run(summary, ())


def _summary_for_records(
    *,
    request: ProviderFetchRequest,
    provider_name: str,
    records: tuple[DatasetRecord, ...],
    model_version: str,
    config_version: str,
    input_fingerprint: str,
) -> DatasetRunSummary:
    counts = {
        RelevanceLabel.RELEVANT: 0,
        RelevanceLabel.NOISE: 0,
        RelevanceLabel.IRRELEVANT: 0,
    }
    for record in records:
        counts[record.relevance] += 1

    return DatasetRunSummary(
        workspace_id=request.workspace_id,
        run_id=request.run_id,
        instrument=request.instrument,
        mode=request.mode,
        timeframe_start=request.timeframe_start,
        timeframe_end=request.timeframe_end,
        status=DatasetRunStatus.COMPLETED,
        provider_name=provider_name,
        record_count=len(records),
        relevant_count=counts[RelevanceLabel.RELEVANT],
        noise_count=counts[RelevanceLabel.NOISE],
        irrelevant_count=counts[RelevanceLabel.IRRELEVANT],
        model_version=model_version,
        config_version=config_version,
        input_fingerprint=input_fingerprint,
    )


def _input_fingerprint(
    *,
    request: ProviderFetchRequest,
    normalized_records: tuple[NormalizedNewsRecord, ...],
    model_version: str,
    config_version: str,
    seed: int,
) -> str:
    material = {
        "workspace_id": request.workspace_id,
        "instrument": request.instrument,
        "mode": request.mode,
        "timeframe_start": request.timeframe_start,
        "timeframe_end": request.timeframe_end,
        "seed": seed,
        "model_version": model_version,
        "config_version": config_version,
        "normalized_records": [
            _normalized_fingerprint_material(record)
            for record in normalized_records
        ],
    }
    return _sha256_stable(material)


def _provider_limitation_fingerprint(
    *,
    request: ProviderFetchRequest,
    provider_name: str,
    reason: str,
    model_version: str,
    config_version: str,
    seed: int,
) -> str:
    material = {
        "workspace_id": request.workspace_id,
        "instrument": request.instrument,
        "mode": request.mode,
        "timeframe_start": request.timeframe_start,
        "timeframe_end": request.timeframe_end,
        "seed": seed,
        "model_version": model_version,
        "config_version": config_version,
        "provider_name": provider_name,
        "provider_limitation_reason": reason,
    }
    return _sha256_stable(material)


def _record_id(
    *,
    provider_name: str,
    normalized_record: NormalizedNewsRecord,
    deterministic_index: int,
    input_fingerprint: str,
) -> str:
    normalized_provider = provider_name.lower().replace(" ", "-")
    if normalized_record.provider_record_id:
        return f"{normalized_provider}:{normalized_record.provider_record_id}"
    material = {
        "input_fingerprint": input_fingerprint,
        "provider_name": provider_name,
        "timestamp": normalized_record.timestamp,
        "headline": normalized_record.headline,
        "source_id": normalized_record.source_id,
        "source_name": normalized_record.source_name,
        "deterministic_index": deterministic_index,
    }
    return f"{normalized_provider}:generated:{_sha256_stable(material)[:16]}"


def _normalized_fingerprint_material(record: NormalizedNewsRecord) -> dict[str, object]:
    return {
        "provider_name": record.provider_name,
        "provider_record_id": record.provider_record_id,
        "timestamp": record.timestamp,
        "headline": record.headline,
        "body": record.body,
        "source_id": record.source_id,
        "source_name": record.source_name,
    }


def _sha256_stable(value: object) -> str:
    return sha256(stable_json_dumps(value).encode("utf-8")).hexdigest()


def metadata_for_preview(
    *,
    preview: DatasetRunPreview,
    seed: int = DEFAULT_DATASET_SEED,
) -> BacktestRunMetadata:
    return BacktestRunMetadata(
        workspace_id=preview.summary.workspace_id,
        run_id=preview.summary.run_id,
        instrument=preview.summary.instrument,
        mode=preview.summary.mode,
        timeframe_start=preview.summary.timeframe_start,
        timeframe_end=preview.summary.timeframe_end,
        seed=seed,
        model_version=preview.summary.model_version,
        config_version=preview.summary.config_version,
        input_fingerprint=preview.summary.input_fingerprint,
    )
