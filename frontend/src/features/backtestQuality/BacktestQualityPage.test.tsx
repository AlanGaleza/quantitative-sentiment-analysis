import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { BacktestQualityPage } from "./BacktestQualityPage";
import type { BacktestQualityReport } from "./types";

const fixtureReport: BacktestQualityReport = {
  workspace_id: "workspace-alpha",
  run_id: "run-001",
  instrument: "BTCUSD",
  mode: "BACKTEST",
  horizon: { value: 4, unit: "hours" },
  model_version: "sentiment-rules-v1",
  config_version: "quality-config-v1",
  metrics: {
    correlation: 0.997,
    hit_rate: 0.75,
    sample_count: 4,
    correlation_pair_count: 3,
    hit_count: 3,
    miss_count: 1,
    missing_movement_count: 1,
    flat_count: 1,
    noise_count: 1,
  },
  warnings: [
    "1 record(s) missing later movement were counted as misses.",
    "1 noise/irrelevant record(s) were preserved but excluded from metric denominators.",
  ],
  chart_points: [
    {
      event_timestamp: "2026-06-08T12:01:00Z",
      sentiment_score: 0.8,
      later_return: 0.04,
      directional_bias: "LONG",
      realized_direction: "UP",
      confidence: 0.75,
      outcome: "HIT",
    },
    {
      event_timestamp: "2026-06-08T12:02:00Z",
      sentiment_score: -0.6,
      later_return: -0.03,
      directional_bias: "SHORT",
      realized_direction: "DOWN",
      confidence: 0.75,
      outcome: "HIT",
    },
    {
      event_timestamp: "2026-06-08T12:03:00Z",
      sentiment_score: 0,
      later_return: 0,
      directional_bias: "FLAT",
      realized_direction: "FLAT",
      confidence: 0.75,
      outcome: "HIT",
    },
    {
      event_timestamp: "2026-06-08T12:04:00Z",
      sentiment_score: 0.5,
      later_return: null,
      directional_bias: "LONG",
      realized_direction: null,
      confidence: 0.75,
      outcome: "MISS",
    },
    {
      event_timestamp: "2026-06-08T12:05:00Z",
      sentiment_score: -0.9,
      later_return: -0.02,
      directional_bias: "SHORT",
      realized_direction: "DOWN",
      confidence: 0.75,
      outcome: "EXCLUDED",
    },
  ],
  representative_records: [
    {
      workspace_id: "workspace-alpha",
      run_id: "run-001",
      record_id: "record-001",
      instrument: "BTCUSD",
      mode: "BACKTEST",
      event_timestamp: "2026-06-08T12:01:00Z",
      headline: "BTCUSD quality fixture 1",
      source_id: null,
      source_name: "Example Crypto News",
      sentiment_score: 0.8,
      directional_bias: "LONG",
      confidence: 0.75,
      relevance: "RELEVANT",
      later_return: 0.04,
      realized_direction: "UP",
      model_version: "sentiment-rules-v1",
      config_version: "quality-config-v1",
    },
    {
      workspace_id: "workspace-alpha",
      run_id: "run-001",
      record_id: "record-004",
      instrument: "BTCUSD",
      mode: "BACKTEST",
      event_timestamp: "2026-06-08T12:04:00Z",
      headline: "BTCUSD quality fixture with missing movement",
      source_id: null,
      source_name: "Example Crypto News",
      sentiment_score: 0.5,
      directional_bias: "LONG",
      confidence: 0.75,
      relevance: "RELEVANT",
      later_return: null,
      realized_direction: null,
      model_version: "sentiment-rules-v1",
      config_version: "quality-config-v1",
    },
  ],
};

describe("BacktestQualityPage", () => {
  it("renders the report contract without recalculating metrics", async () => {
    const loadReport = vi.fn().mockResolvedValue(fixtureReport);

    render(
      <BacktestQualityPage
        workspaceId="workspace-alpha"
        runId="run-001"
        loadReport={loadReport}
      />,
    );

    expect(
      await screen.findByRole("heading", { name: "Backtest quality report" }),
    ).toBeInTheDocument();
    expect(loadReport).toHaveBeenCalledWith("workspace-alpha", "run-001");
    expect(screen.getByText("BACKTEST-only analytical dataset quality indicator", {
      exact: false,
    })).toBeInTheDocument();
    expect(screen.queryByText(/recommendation/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/signal/i)).not.toBeInTheDocument();

    const metrics = screen.getByLabelText("Quality metrics");
    expect(within(metrics).getByText("75.0%")).toBeInTheDocument();
    expect(within(metrics).getByText("0.997")).toBeInTheDocument();
    expect(within(metrics).getByText("Missing movement counted as miss")).toBeInTheDocument();
    expect(within(metrics).getByText("1 total misses")).toBeInTheDocument();

    expect(screen.getByText("4 hours")).toBeInTheDocument();
    expect(screen.getByText("sentiment-rules-v1")).toBeInTheDocument();
    expect(screen.getByText("quality-config-v1")).toBeInTheDocument();
    expect(screen.getByText("BTCUSD quality fixture with missing movement")).toBeInTheDocument();
    expect(screen.getAllByText("missing").length).toBeGreaterThan(0);
    expect(screen.getByText(/counted as misses/i)).toBeInTheDocument();
  });

  it("renders API errors", async () => {
    const loadReport = vi.fn().mockRejectedValue(
      new Error("S-02 deterministic completed-run storage is not integrated yet"),
    );

    render(
      <BacktestQualityPage
        workspaceId="workspace-alpha"
        runId="run-001"
        loadReport={loadReport}
      />,
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "S-02 deterministic completed-run storage is not integrated yet",
    );
  });

  it("renders empty report sections", async () => {
    const emptyReport: BacktestQualityReport = {
      ...fixtureReport,
      metrics: {
        ...fixtureReport.metrics,
        correlation: null,
        hit_rate: null,
        sample_count: 0,
        correlation_pair_count: 0,
        hit_count: 0,
        miss_count: 0,
        missing_movement_count: 0,
        flat_count: 0,
        noise_count: 0,
      },
      warnings: [],
      chart_points: [],
      representative_records: [],
    };
    const loadReport = vi.fn().mockResolvedValue(emptyReport);

    render(
      <BacktestQualityPage
        workspaceId="workspace-alpha"
        runId="run-001"
        loadReport={loadReport}
      />,
    );

    expect(await screen.findByText("No warnings for this BACKTEST report.")).toBeInTheDocument();
    expect(
      screen.getByText("No chart points are available for this BACKTEST report."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("No representative records are available for this BACKTEST report."),
    ).toBeInTheDocument();
  });
});
