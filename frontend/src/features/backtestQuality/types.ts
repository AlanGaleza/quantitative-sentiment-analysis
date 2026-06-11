export type DirectionalBias = "LONG" | "SHORT" | "FLAT";
export type RealizedDirection = "UP" | "DOWN" | "FLAT";
export type RelevanceLabel = "RELEVANT" | "NOISE" | "IRRELEVANT";
export type EvaluationOutcome = "HIT" | "MISS" | "EXCLUDED";
export type HorizonUnit = "minutes" | "hours" | "days";

export interface QualityHorizon {
  value: number;
  unit: HorizonUnit;
}

export interface QualityInputRecord {
  workspace_id: string;
  run_id: string;
  record_id: string | null;
  instrument: "BTCUSD";
  mode: "BACKTEST";
  event_timestamp: string;
  headline: string;
  source_id: string | null;
  source_name: string | null;
  sentiment_score: number;
  directional_bias: DirectionalBias;
  confidence: number;
  relevance: RelevanceLabel;
  later_return: number | null;
  realized_direction: RealizedDirection | null;
  model_version: string;
  config_version: string;
}

export interface QualityChartPoint {
  event_timestamp: string;
  sentiment_score: number;
  later_return: number | null;
  directional_bias: DirectionalBias;
  realized_direction: RealizedDirection | null;
  confidence: number;
  outcome: EvaluationOutcome;
}

export interface QualityMetrics {
  correlation: number | null;
  hit_rate: number | null;
  sample_count: number;
  correlation_pair_count: number;
  hit_count: number;
  miss_count: number;
  missing_movement_count: number;
  flat_count: number;
  noise_count: number;
}

export interface BacktestQualityReport {
  workspace_id: string;
  run_id: string;
  instrument: "BTCUSD";
  mode: "BACKTEST";
  horizon: QualityHorizon;
  model_version: string;
  config_version: string;
  metrics: QualityMetrics;
  warnings: string[];
  chart_points: QualityChartPoint[];
  representative_records: QualityInputRecord[];
}
