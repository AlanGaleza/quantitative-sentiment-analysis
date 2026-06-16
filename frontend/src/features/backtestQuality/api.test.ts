import { afterEach, describe, expect, it, vi } from "vitest";

import {
  QualityReportApiError,
  buildBacktestQualityReportUrl,
  fetchBacktestQualityReport,
} from "./api";

describe("backtest quality API client", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("uses VITE_API_BASE_URL when set", () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test/");

    expect(buildBacktestQualityReportUrl("workspace alpha", "run/001")).toBe(
      "https://api.example.test/api/workspaces/workspace%20alpha/backtests/run%2F001/quality",
    );
    expect(
      buildBacktestQualityReportUrl("workspace alpha", "run/001", {
        value: 1,
        unit: "minutes",
      }),
    ).toBe(
      "https://api.example.test/api/workspaces/workspace%20alpha/backtests/run%2F001/quality?horizon_value=1&horizon_unit=minutes",
    );
  });

  it("falls back to relative /api for local Vite proxy development", () => {
    vi.stubEnv("VITE_API_BASE_URL", "");

    expect(buildBacktestQualityReportUrl("workspace-alpha", "run-001")).toBe(
      "/api/workspaces/workspace-alpha/backtests/run-001/quality",
    );
    expect(
      buildBacktestQualityReportUrl("workspace-alpha", "run-001", {
        value: 4,
        unit: "hours",
      }),
    ).toBe(
      "/api/workspaces/workspace-alpha/backtests/run-001/quality?horizon_value=4&horizon_unit=hours",
    );
  });

  it("raises typed errors for non-2xx responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "S-02 integration is not ready" }), {
          status: 409,
          headers: { "content-type": "application/json" },
        }),
      ),
    );

    await expect(
      fetchBacktestQualityReport("workspace-alpha", "run-001"),
    ).rejects.toMatchObject({
      status: 409,
      detail: "S-02 integration is not ready",
    } satisfies Partial<QualityReportApiError>);
  });

  it("fetches quality reports with cookies", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          workspace_id: "workspace-alpha",
          run_id: "run-001",
          instrument: "BTCUSD",
          mode: "BACKTEST",
          horizon: { value: 24, unit: "hours" },
          model_version: "sentiment-rules-v1",
          config_version: "news-sentiment-policy-v1",
          metrics: {
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
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchBacktestQualityReport("workspace-alpha", "run-001");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/workspaces/workspace-alpha/backtests/run-001/quality",
      {
        credentials: "include",
        headers: {
          Accept: "application/json",
        },
      },
    );
  });

  it("fetches selected horizon reports with cookies", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          workspace_id: "workspace-alpha",
          run_id: "run-001",
          instrument: "BTCUSD",
          mode: "BACKTEST",
          horizon: { value: 1, unit: "minutes" },
          model_version: "sentiment-rules-v1",
          config_version: "news-sentiment-policy-v1",
          metrics: {
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
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchBacktestQualityReport("workspace-alpha", "run-001", {
      value: 1,
      unit: "minutes",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/workspaces/workspace-alpha/backtests/run-001/quality?horizon_value=1&horizon_unit=minutes",
      {
        credentials: "include",
        headers: {
          Accept: "application/json",
        },
      },
    );
  });
});
