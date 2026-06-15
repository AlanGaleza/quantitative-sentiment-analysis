export type BacktestRunStatus = "DRAFT" | "READY_FOR_DATASET";

export interface CreateBacktestRunRequest {
  instrument: "BTCUSD";
  mode: "BACKTEST";
  timeframe_start: string;
  timeframe_end: string;
}

export interface BacktestRunShell {
  workspace_id: string;
  run_id: string;
  instrument: "BTCUSD";
  mode: "BACKTEST";
  timeframe_start: string;
  timeframe_end: string;
  status: BacktestRunStatus;
  created_at: string;
  quality_report_path: string | null;
}

export type DatasetRunStatus =
  | "DRAFT"
  | "RUNNING"
  | "COMPLETED"
  | "FAILED_PROVIDER_LIMITATION";

export type DirectionalBias = "LONG" | "SHORT" | "FLAT";
export type RelevanceLabel = "RELEVANT" | "NOISE" | "IRRELEVANT";

export interface DatasetProviderLimitation {
  provider_name: string;
  reason: string;
  detail: string | null;
}

export interface DatasetRunSummary {
  workspace_id: string;
  run_id: string;
  instrument: "BTCUSD";
  mode: "BACKTEST";
  timeframe_start: string;
  timeframe_end: string;
  status: DatasetRunStatus;
  provider_name: string;
  record_count: number;
  relevant_count: number;
  noise_count: number;
  irrelevant_count: number;
  model_version: string;
  config_version: string;
  input_fingerprint: string;
  provider_limitation: DatasetProviderLimitation | null;
}

export interface DatasetPreviewRecord {
  workspace_id: string;
  run_id: string;
  record_id: string | null;
  timestamp: string;
  headline: string;
  source_id: string | null;
  source_name: string | null;
  instrument: "BTCUSD";
  mode: "BACKTEST";
  sentiment_score: number;
  directional_bias: DirectionalBias;
  confidence: number;
  relevance: RelevanceLabel;
  model_version: string;
  config_version: string;
}

export interface DatasetRunPreview {
  summary: DatasetRunSummary;
  records: DatasetPreviewRecord[];
}
