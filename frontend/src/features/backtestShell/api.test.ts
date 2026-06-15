import { afterEach, describe, expect, it, vi } from "vitest";

import {
  BacktestShellApiError,
  buildBacktestDatasetUrl,
  buildBacktestRunShellUrl,
  buildCreateBacktestRunUrl,
  buildRunBacktestDatasetUrl,
  createBacktestRunShell,
  fetchBacktestRunShell,
  fetchBacktestDataset,
  runBacktestDataset,
} from "./api";
import type { CreateBacktestRunRequest } from "./types";

const REQUEST: CreateBacktestRunRequest = {
  instrument: "BTCUSD",
  mode: "BACKTEST",
  timeframe_start: "2026-06-01T12:00:00Z",
  timeframe_end: "2026-06-08T12:00:00Z",
};

describe("backtest shell API client", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("uses VITE_API_BASE_URL when set", () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test/");

    expect(buildCreateBacktestRunUrl("workspace alpha")).toBe(
      "https://api.example.test/api/workspaces/workspace%20alpha/backtests/drafts",
    );
    expect(buildBacktestRunShellUrl("workspace alpha", "draft run/001")).toBe(
      "https://api.example.test/api/workspaces/workspace%20alpha/backtests/draft%20run%2F001",
    );
    expect(buildRunBacktestDatasetUrl("workspace alpha", "draft run/001")).toBe(
      "https://api.example.test/api/workspaces/workspace%20alpha/backtests/draft%20run%2F001/dataset/run",
    );
    expect(buildBacktestDatasetUrl("workspace alpha", "draft run/001")).toBe(
      "https://api.example.test/api/workspaces/workspace%20alpha/backtests/draft%20run%2F001/dataset",
    );
  });

  it("falls back to relative /api for local Vite proxy development", () => {
    vi.stubEnv("VITE_API_BASE_URL", "");

    expect(buildCreateBacktestRunUrl("workspace-alpha")).toBe(
      "/api/workspaces/workspace-alpha/backtests/drafts",
    );
    expect(buildBacktestRunShellUrl("workspace-alpha", "draft-run-001")).toBe(
      "/api/workspaces/workspace-alpha/backtests/draft-run-001",
    );
    expect(buildRunBacktestDatasetUrl("workspace-alpha", "draft-run-001")).toBe(
      "/api/workspaces/workspace-alpha/backtests/draft-run-001/dataset/run",
    );
    expect(buildBacktestDatasetUrl("workspace-alpha", "draft-run-001")).toBe(
      "/api/workspaces/workspace-alpha/backtests/draft-run-001/dataset",
    );
  });

  it("posts JSON to create a draft run shell", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          workspace_id: "workspace-alpha",
          run_id: "draft-run-001",
          instrument: "BTCUSD",
          mode: "BACKTEST",
          timeframe_start: REQUEST.timeframe_start,
          timeframe_end: REQUEST.timeframe_end,
          status: "DRAFT",
          created_at: "2026-06-08T12:30:00Z",
          quality_report_path:
            "/workspaces/workspace-alpha/backtests/draft-run-001/quality",
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const run = await createBacktestRunShell("workspace-alpha", REQUEST);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/workspaces/workspace-alpha/backtests/drafts",
      {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify(REQUEST),
      },
    );
    expect(run.run_id).toBe("draft-run-001");
    expect(run.status).toBe("DRAFT");
  });

  it("fetches an existing draft run shell without using quality endpoints", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          workspace_id: "workspace-alpha",
          run_id: "draft-run-001",
          instrument: "BTCUSD",
          mode: "BACKTEST",
          timeframe_start: REQUEST.timeframe_start,
          timeframe_end: REQUEST.timeframe_end,
          status: "DRAFT",
          created_at: "2026-06-08T12:30:00Z",
          quality_report_path:
            "/workspaces/workspace-alpha/backtests/draft-run-001/quality",
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchBacktestRunShell("workspace-alpha", "draft-run-001");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/workspaces/workspace-alpha/backtests/draft-run-001",
      {
        headers: {
          Accept: "application/json",
        },
      },
    );
    expect(fetchMock.mock.calls[0][0]).not.toContain("/quality");
  });

  it("starts deterministic dataset generation without using quality endpoints", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(datasetPreview()), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const preview = await runBacktestDataset("workspace-alpha", "draft-run-001");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/workspaces/workspace-alpha/backtests/draft-run-001/dataset/run",
      {
        method: "POST",
        headers: {
          Accept: "application/json",
        },
      },
    );
    expect(fetchMock.mock.calls[0][0]).not.toContain("/quality");
    expect(preview.summary.status).toBe("COMPLETED");
    expect(preview.records[0].directional_bias).toBe("LONG");
  });

  it("fetches completed deterministic dataset preview", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(datasetPreview()), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const preview = await fetchBacktestDataset("workspace-alpha", "draft-run-001");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/workspaces/workspace-alpha/backtests/draft-run-001/dataset",
      {
        headers: {
          Accept: "application/json",
        },
      },
    );
    expect(preview.summary.record_count).toBe(1);
  });

  it("raises typed errors for non-2xx responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "timeframe range is invalid" }), {
          status: 422,
          headers: { "content-type": "application/json" },
        }),
      ),
    );

    await expect(
      createBacktestRunShell("workspace-alpha", REQUEST),
    ).rejects.toMatchObject({
      status: 422,
      detail: "timeframe range is invalid",
    } satisfies Partial<BacktestShellApiError>);
  });

  it("raises typed provider limitation errors with dataset preview payload", async () => {
    const failedPreview = datasetPreview({
      summary: {
        ...datasetPreview().summary,
        status: "FAILED_PROVIDER_LIMITATION",
        provider_name: "CryptoPanic",
        record_count: 0,
        relevant_count: 0,
        noise_count: 0,
        irrelevant_count: 0,
        provider_limitation: {
          provider_name: "CryptoPanic",
          reason: "missing provider configuration",
          detail: "Set CRYPTOPANIC_API_KEY locally for a BACKTEST smoke check.",
        },
      },
      records: [],
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: failedPreview }), {
          status: 409,
          headers: { "content-type": "application/json" },
        }),
      ),
    );

    await expect(
      runBacktestDataset("workspace-alpha", "draft-run-001"),
    ).rejects.toMatchObject({
      status: 409,
      detail:
        "CryptoPanic: missing provider configuration: Set CRYPTOPANIC_API_KEY locally for a BACKTEST smoke check.",
      payload: failedPreview,
    } satisfies Partial<BacktestShellApiError>);
  });
});

function datasetPreview(overrides: Record<string, unknown> = {}) {
  return {
    summary: {
      workspace_id: "workspace-alpha",
      run_id: "draft-run-001",
      instrument: "BTCUSD",
      mode: "BACKTEST",
      timeframe_start: REQUEST.timeframe_start,
      timeframe_end: REQUEST.timeframe_end,
      status: "COMPLETED",
      provider_name: "FixtureNews",
      record_count: 1,
      relevant_count: 1,
      noise_count: 0,
      irrelevant_count: 0,
      model_version: "sentiment-rules-v1",
      config_version: "news-sentiment-policy-v1",
      input_fingerprint: "fingerprint-alpha",
      provider_limitation: null,
    },
    records: [
      {
        workspace_id: "workspace-alpha",
        run_id: "draft-run-001",
        record_id: "fixturenews:record-001",
        timestamp: "2026-06-02T09:00:00Z",
        headline: "Bitcoin ETF approval sparks bullish inflows",
        source_id: "coinwire",
        source_name: "CoinWire",
        instrument: "BTCUSD",
        mode: "BACKTEST",
        sentiment_score: 0.57,
        directional_bias: "LONG",
        confidence: 0.78,
        relevance: "RELEVANT",
        model_version: "sentiment-rules-v1",
        config_version: "news-sentiment-policy-v1",
      },
    ],
    ...overrides,
  };
}
