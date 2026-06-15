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
