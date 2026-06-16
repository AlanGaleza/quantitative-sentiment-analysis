import { afterEach, describe, expect, it, vi } from "vitest";

import {
  BacktestConfigApiError,
  buildBacktestConfigDetailUrl,
  buildBacktestConfigDraftUrl,
  buildBacktestConfigListUrl,
  createBacktestConfig,
  createDraftFromBacktestConfig,
  deleteBacktestConfig,
  listBacktestConfigs,
  updateBacktestConfig,
} from "./api";

const REQUEST = {
  name: "Baseline BTC config",
  instrument: "BTCUSD" as const,
  mode: "BACKTEST" as const,
  timeframe_start: "2026-06-01T12:00:00.000Z",
  timeframe_end: "2026-06-08T12:00:00.000Z",
};

describe("backtest config API client", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("builds config URLs from VITE_API_BASE_URL", () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test/");

    expect(buildBacktestConfigListUrl("workspace alpha")).toBe(
      "https://api.example.test/api/workspaces/workspace%20alpha/backtest-configs",
    );
    expect(buildBacktestConfigDetailUrl("workspace alpha", "config/001")).toBe(
      "https://api.example.test/api/workspaces/workspace%20alpha/backtest-configs/config%2F001",
    );
    expect(buildBacktestConfigDraftUrl("workspace alpha", "config/001")).toBe(
      "https://api.example.test/api/workspaces/workspace%20alpha/backtest-configs/config%2F001/drafts",
    );
  });

  it("lists saved configurations with cookies", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([configResponse()]), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const configs = await listBacktestConfigs("workspace-alpha");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/workspaces/workspace-alpha/backtest-configs",
      {
        credentials: "include",
        headers: {
          Accept: "application/json",
        },
      },
    );
    expect(configs[0].name).toBe("Baseline BTC config");
  });

  it("creates and updates saved configurations with JSON and cookies", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify(configResponse()), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(configResponse({ name: "Renamed config" })), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await createBacktestConfig("workspace-alpha", REQUEST);
    await updateBacktestConfig("workspace-alpha", "config-001", {
      name: "Renamed config",
    });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/workspaces/workspace-alpha/backtest-configs",
      {
        method: "POST",
        credentials: "include",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify(REQUEST),
      },
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/workspaces/workspace-alpha/backtest-configs/config-001",
      {
        method: "PUT",
        credentials: "include",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name: "Renamed config" }),
      },
    );
  });

  it("deletes saved configurations and accepts an empty 204 response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      deleteBacktestConfig("workspace-alpha", "config-001"),
    ).resolves.toBeUndefined();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/workspaces/workspace-alpha/backtest-configs/config-001",
      {
        method: "DELETE",
        credentials: "include",
        headers: {
          Accept: "application/json",
        },
      },
    );
  });

  it("creates a draft run from a saved configuration", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(draftRun()), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const run = await createDraftFromBacktestConfig(
      "workspace-alpha",
      "config-001",
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/workspaces/workspace-alpha/backtest-configs/config-001/drafts",
      {
        method: "POST",
        credentials: "include",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({}),
      },
    );
    expect(run.run_id).toBe("draft-run-001");
  });

  it("raises typed errors for non-2xx responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "saved config was not found" }), {
          status: 404,
          headers: { "content-type": "application/json" },
        }),
      ),
    );

    await expect(
      deleteBacktestConfig("workspace-alpha", "missing-config"),
    ).rejects.toMatchObject({
      status: 404,
      detail: "saved config was not found",
    } satisfies Partial<BacktestConfigApiError>);
  });
});

function configResponse(overrides: Record<string, unknown> = {}) {
  return {
    id: "config-001",
    workspace_id: "workspace-alpha",
    name: "Baseline BTC config",
    instrument: "BTCUSD",
    mode: "BACKTEST",
    timeframe_start: REQUEST.timeframe_start,
    timeframe_end: REQUEST.timeframe_end,
    created_at: "2026-06-08T12:30:00.000Z",
    updated_at: "2026-06-08T12:30:00.000Z",
    ...overrides,
  };
}

function draftRun() {
  return {
    workspace_id: "workspace-alpha",
    run_id: "draft-run-001",
    instrument: "BTCUSD",
    mode: "BACKTEST",
    timeframe_start: REQUEST.timeframe_start,
    timeframe_end: REQUEST.timeframe_end,
    status: "DRAFT",
    created_at: "2026-06-08T12:30:00.000Z",
    quality_report_path:
      "/workspaces/workspace-alpha/backtests/draft-run-001/quality",
  };
}
