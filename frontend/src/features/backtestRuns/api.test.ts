import { afterEach, describe, expect, it, vi } from "vitest";

import {
  BacktestRunHistoryApiError,
  buildBacktestRunHistoryUrl,
  fetchBacktestRunHistory,
} from "./api";

describe("backtest run history API client", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("uses VITE_API_BASE_URL when set", () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test/");

    expect(buildBacktestRunHistoryUrl("workspace alpha")).toBe(
      "https://api.example.test/api/workspaces/workspace%20alpha/backtests",
    );
  });

  it("falls back to relative /api for local Vite proxy development", () => {
    vi.stubEnv("VITE_API_BASE_URL", "");

    expect(buildBacktestRunHistoryUrl("workspace-alpha")).toBe(
      "/api/workspaces/workspace-alpha/backtests",
    );
  });

  it("fetches workspace run history with cookie credentials", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(historyResponse()), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const history = await fetchBacktestRunHistory("workspace-alpha");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/workspaces/workspace-alpha/backtests",
      {
        credentials: "include",
        headers: {
          Accept: "application/json",
        },
      },
    );
    expect(history.workspace_id).toBe("workspace-alpha");
    expect(history.runs[0].run_id).toBe("draft-run-001");
  });

  it("raises typed errors for non-2xx responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "workspace was not found" }), {
          status: 404,
          headers: { "content-type": "application/json" },
        }),
      ),
    );

    await expect(
      fetchBacktestRunHistory("workspace-alpha"),
    ).rejects.toMatchObject({
      status: 404,
      detail: "workspace was not found",
    } satisfies Partial<BacktestRunHistoryApiError>);
  });

  it("raises typed errors for empty successful responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 200 })),
    );

    await expect(
      fetchBacktestRunHistory("workspace-alpha"),
    ).rejects.toMatchObject({
      status: 200,
      detail: "BACKTEST run history response was empty.",
    } satisfies Partial<BacktestRunHistoryApiError>);
  });
});

function historyResponse() {
  return {
    workspace_id: "workspace-alpha",
    runs: [
      {
        workspace_id: "workspace-alpha",
        run_id: "draft-run-001",
        config_id: "config-001",
        config_name: "Config One",
        instrument: "BTCUSD",
        mode: "BACKTEST",
        timeframe_start: "2026-06-01T12:00:00Z",
        timeframe_end: "2026-06-08T12:00:00Z",
        status: "DRAFT",
        created_at: "2026-06-08T12:30:00Z",
        dataset_status: "COMPLETED",
        provider_name: "Sharpe Terminal",
        record_count: 2,
        relevant_count: 1,
        noise_count: 1,
        irrelevant_count: 0,
        model_version: "sentiment-rules-v1",
        config_version: "news-sentiment-policy-v1",
        input_fingerprint: "fingerprint-alpha",
        provider_limitation: null,
        dataset_preview_path:
          "/api/workspaces/workspace-alpha/backtests/draft-run-001/dataset",
        dataset_export_path:
          "/api/workspaces/workspace-alpha/backtests/draft-run-001/dataset/export.jsonl",
        quality_report_path:
          "/workspaces/workspace-alpha/backtests/draft-run-001/quality",
      },
    ],
  };
}
