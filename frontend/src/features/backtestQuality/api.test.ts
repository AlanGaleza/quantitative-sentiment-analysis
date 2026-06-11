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
  });

  it("falls back to relative /api for local Vite proxy development", () => {
    vi.stubEnv("VITE_API_BASE_URL", "");

    expect(buildBacktestQualityReportUrl("workspace-alpha", "run-001")).toBe(
      "/api/workspaces/workspace-alpha/backtests/run-001/quality",
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
});
