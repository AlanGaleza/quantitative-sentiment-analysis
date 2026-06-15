import { afterEach, describe, expect, it, vi } from "vitest";

import {
  BacktestShellApiError,
  buildBacktestRunShellUrl,
  buildCreateBacktestRunUrl,
  createBacktestRunShell,
  fetchBacktestRunShell,
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
  });

  it("falls back to relative /api for local Vite proxy development", () => {
    vi.stubEnv("VITE_API_BASE_URL", "");

    expect(buildCreateBacktestRunUrl("workspace-alpha")).toBe(
      "/api/workspaces/workspace-alpha/backtests/drafts",
    );
    expect(buildBacktestRunShellUrl("workspace-alpha", "draft-run-001")).toBe(
      "/api/workspaces/workspace-alpha/backtests/draft-run-001",
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
});
