import type {
  BacktestRunStatus,
  DatasetProviderLimitation,
  DatasetRunStatus,
} from "../backtestShell/types";

export interface BacktestRunHistoryItem {
  workspace_id: string;
  run_id: string;
  config_id: string | null;
  config_name: string | null;
  instrument: "BTCUSD";
  mode: "BACKTEST";
  timeframe_start: string;
  timeframe_end: string;
  status: BacktestRunStatus;
  created_at: string;
  dataset_status: DatasetRunStatus | null;
  provider_name: string | null;
  record_count: number | null;
  relevant_count: number | null;
  noise_count: number | null;
  irrelevant_count: number | null;
  model_version: string | null;
  config_version: string | null;
  input_fingerprint: string | null;
  provider_limitation: DatasetProviderLimitation | null;
  dataset_preview_path: string | null;
  dataset_export_path: string | null;
  quality_report_path: string | null;
}

export interface BacktestRunHistoryResponse {
  workspace_id: string;
  runs: BacktestRunHistoryItem[];
}
