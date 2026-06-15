import { afterEach, describe, expect, it, vi } from "vitest";

import {
  BacktestShellApiError,
  buildBacktestDatasetExportUrl,
  buildBacktestDatasetUrl,
  buildBacktestRunShellUrl,
  buildCreateBacktestRunUrl,
  buildRunBacktestDatasetUrl,
  createBacktestRunShell,
  downloadBacktestDatasetExport,
  downloadBlob,
  fetchBacktestDatasetExport,
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
    expect(buildBacktestDatasetExportUrl("workspace alpha", "draft run/001")).toBe(
      "https://api.example.test/api/workspaces/workspace%20alpha/backtests/draft%20run%2F001/dataset/export.jsonl",
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
    expect(buildBacktestDatasetExportUrl("workspace-alpha", "draft-run-001")).toBe(
      "/api/workspaces/workspace-alpha/backtests/draft-run-001/dataset/export.jsonl",
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

  it("fetches completed deterministic dataset JSONL export as a blob", async () => {
    const body = '{"run_id":"draft-run-001"}\n';
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(body, {
        status: 200,
        headers: { "content-type": "application/x-ndjson" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const blob = await fetchBacktestDatasetExport(
      "workspace-alpha",
      "draft-run-001",
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/workspaces/workspace-alpha/backtests/draft-run-001/dataset/export.jsonl",
      {
        headers: {
          Accept: "application/x-ndjson",
        },
      },
    );
    expect(await blob.text()).toBe(body);
  });

  it("downloads completed deterministic dataset JSONL export with a stable filename", async () => {
    const body = '{"run_id":"draft-run-001"}\n';
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(body, {
          status: 200,
          headers: { "content-type": "application/x-ndjson" },
        }),
      ),
    );
    const createObjectUrl = vi.fn().mockReturnValue("blob:dataset-export");
    const revokeObjectUrl = vi.fn();
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: createObjectUrl,
      revokeObjectURL: revokeObjectUrl,
    });
    const click = vi.fn();
    const createElement = vi
      .spyOn(document, "createElement")
      .mockImplementation((tagName: string) => {
        const element = document.createElementNS(
          "http://www.w3.org/1999/xhtml",
          tagName,
        ) as HTMLAnchorElement;
        if (tagName === "a") {
          element.click = click;
        }
        return element;
      });

    await downloadBacktestDatasetExport("workspace alpha", "draft/run 001");

    expect(createObjectUrl).toHaveBeenCalledOnce();
    expect(await createObjectUrl.mock.calls[0][0].text()).toBe(body);
    expect(click).toHaveBeenCalledOnce();
    const anchor = createElement.mock.results[0].value as HTMLAnchorElement;
    expect(anchor.download).toBe("workspace_alpha-draft_run_001-dataset.jsonl");
    expect(revokeObjectUrl).toHaveBeenCalledWith("blob:dataset-export");
    expect(document.body.querySelector("a[download]")).not.toBeInTheDocument();
  });

  it("can trigger a browser download for a provided blob", () => {
    const createObjectUrl = vi.fn().mockReturnValue("blob:manual-export");
    const revokeObjectUrl = vi.fn();
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: createObjectUrl,
      revokeObjectURL: revokeObjectUrl,
    });
    const click = vi.fn();
    vi.spyOn(document, "createElement").mockImplementation((tagName: string) => {
      const element = document.createElementNS(
        "http://www.w3.org/1999/xhtml",
        tagName,
      ) as HTMLAnchorElement;
      if (tagName === "a") {
        element.click = click;
      }
      return element;
    });
    const blob = new Blob(['{"run_id":"draft-run-001"}\n'], {
      type: "application/x-ndjson",
    });

    downloadBlob(blob, "workspace-alpha-draft-run-001-dataset.jsonl");

    expect(createObjectUrl).toHaveBeenCalledWith(blob);
    expect(click).toHaveBeenCalledOnce();
    expect(revokeObjectUrl).toHaveBeenCalledWith("blob:manual-export");
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

  it("raises typed export errors for non-2xx JSONL export responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "dataset export is not ready" }), {
          status: 409,
          headers: { "content-type": "application/json" },
        }),
      ),
    );

    await expect(
      fetchBacktestDatasetExport("workspace-alpha", "draft-run-001"),
    ).rejects.toMatchObject({
      status: 409,
      detail: "dataset export is not ready",
    } satisfies Partial<BacktestShellApiError>);
  });

  it("raises typed provider limitation errors with dataset preview payload", async () => {
    const failedPreview = datasetPreview({
      summary: {
        ...datasetPreview().summary,
        status: "FAILED_PROVIDER_LIMITATION",
        provider_name: "Sharpe Terminal",
        record_count: 0,
        relevant_count: 0,
        noise_count: 0,
        irrelevant_count: 0,
        provider_limitation: {
          provider_name: "Sharpe Terminal",
          reason: "missing provider configuration",
          detail: "Set SHARPE_API_KEY locally for a BACKTEST smoke check.",
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
        "Sharpe Terminal: missing provider configuration: Set SHARPE_API_KEY locally for a BACKTEST smoke check.",
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
