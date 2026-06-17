import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { BacktestShellPage } from "./BacktestShellPage";
import type {
  BacktestRunShell,
  CreateBacktestRunRequest,
  DatasetRunPreview,
} from "./types";

const FIXED_NOW = new Date("2026-06-15T10:00:00.000Z");
const DEFAULT_START = "2026-05-16T10:00:00.000Z";
const DEFAULT_END = "2026-06-15T10:00:00.000Z";

function createdRun(
  request: CreateBacktestRunRequest,
  overrides: Partial<BacktestRunShell> = {},
): BacktestRunShell {
  return {
    workspace_id: "workspace-alpha",
    run_id: "draft-run-001",
    instrument: "BTCUSD",
    mode: "BACKTEST",
    timeframe_start: request.timeframe_start,
    timeframe_end: request.timeframe_end,
    status: "DRAFT",
    created_at: "2026-06-15T10:01:00.000Z",
    quality_report_path:
      "/workspaces/workspace-alpha/backtests/draft-run-001/quality",
    ...overrides,
  };
}

describe("BacktestShellPage", () => {
  it("renders default 30-day BTCUSD BACKTEST values from an injected reference time", () => {
    render(<BacktestShellPage workspaceId="workspace-alpha" now={FIXED_NOW} />);

    expect(
      screen.getByRole("heading", { name: "Workspace backtest shell" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Workspace")).toHaveValue("workspace-alpha");
    expect(screen.getByLabelText("Instrument")).toHaveValue("BTCUSD");
    expect(screen.getByLabelText("Mode")).toHaveValue("BACKTEST");
    expect(screen.getByLabelText("Status")).toHaveValue("DRAFT");
    expect(screen.getByLabelText("Timeframe start")).toHaveValue(DEFAULT_START);
    expect(screen.getByLabelText("Timeframe end")).toHaveValue(DEFAULT_END);
  });

  it("creates a draft run and displays returned metadata", async () => {
    const createRun = vi
      .fn()
      .mockImplementation(
        async (_workspaceId: string, request: CreateBacktestRunRequest) =>
          createdRun(request),
      );
    render(
      <BacktestShellPage
        workspaceId="workspace-alpha"
        now={FIXED_NOW}
        createRun={createRun}
      />,
    );

    fireEvent.change(screen.getByLabelText("Timeframe start"), {
      target: { value: "2026-06-01T12:00:00.000Z" },
    });
    fireEvent.change(screen.getByLabelText("Timeframe end"), {
      target: { value: "2026-06-08T12:00:00.000Z" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create draft run" }));

    expect(await screen.findByText("Draft run created")).toBeInTheDocument();
    expect(createRun).toHaveBeenCalledWith("workspace-alpha", {
      instrument: "BTCUSD",
      mode: "BACKTEST",
      timeframe_start: "2026-06-01T12:00:00.000Z",
      timeframe_end: "2026-06-08T12:00:00.000Z",
    });

    const metadata = screen.getByLabelText("Created run metadata");
    expect(within(metadata).getByText("draft-run-001")).toBeInTheDocument();
    expect(within(metadata).getAllByText("workspace-alpha").length).toBeGreaterThan(0);
    expect(within(metadata).getAllByText("BTCUSD").length).toBeGreaterThan(0);
    expect(within(metadata).getAllByText("BACKTEST").length).toBeGreaterThan(0);
    expect(within(metadata).getAllByText("DRAFT").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Quality route" })).toHaveAttribute(
      "href",
      "/workspaces/workspace-alpha/backtests/draft-run-001/quality",
    );
    expect(
      screen.getByText(
        /unavailable until this BACKTEST run has a completed deterministic dataset/i,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Run deterministic BACKTEST dataset" }),
    ).toBeInTheDocument();
  });

  it("runs deterministic dataset after draft creation and displays summary preview", async () => {
    const createRun = vi
      .fn()
      .mockImplementation(
        async (_workspaceId: string, request: CreateBacktestRunRequest) =>
          createdRun(request),
      );
    const runDataset = vi.fn().mockResolvedValue(datasetPreview());
    const downloadDatasetExport = vi.fn().mockResolvedValue(undefined);
    render(
      <BacktestShellPage
        workspaceId="workspace-alpha"
        now={FIXED_NOW}
        createRun={createRun}
        runDataset={runDataset}
        downloadDatasetExport={downloadDatasetExport}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Create draft run" }));
    await screen.findByText("Draft run created");
    fireEvent.click(
      screen.getByRole("button", { name: "Run deterministic BACKTEST dataset" }),
    );

    expect(
      await screen.findByText("Completed deterministic dataset"),
    ).toBeInTheDocument();
    expect(runDataset).toHaveBeenCalledWith("workspace-alpha", "draft-run-001");

    const summary = screen.getByLabelText("Dataset summary metadata");
    expect(within(summary).getByText("FixtureNews")).toBeInTheDocument();
    expect(within(summary).getByText("2")).toBeInTheDocument();
    expect(within(summary).getByText("sentiment-rules-v1")).toBeInTheDocument();
    expect(within(summary).getByText("news-sentiment-policy-v1")).toBeInTheDocument();
    expect(within(summary).getByText("fingerprint-alpha")).toBeInTheDocument();
    expect(screen.getByText("Bitcoin ETF approval sparks bullish inflows")).toBeInTheDocument();
    expect(screen.getByText("Provider placeholder")).toBeInTheDocument();
    expect(screen.getByText("LONG")).toBeInTheDocument();
    expect(screen.getByText("NOISE")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Quality route" })).toHaveAttribute(
      "href",
      "/workspaces/workspace-alpha/backtests/draft-run-001/quality",
    );
    expect(
      screen.getByText(/available for this completed dataset/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/Movement fields remain pending price enrichment/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Download JSONL dataset" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(
        /unavailable until this BACKTEST run has a completed deterministic dataset/i,
      ),
    ).not.toBeInTheDocument();
  });

  it("renders preview records inside a scrollable table region", async () => {
    const createRun = vi
      .fn()
      .mockImplementation(
        async (_workspaceId: string, request: CreateBacktestRunRequest) =>
          createdRun(request),
      );
    const preview = datasetPreview({
      records: Array.from({ length: 12 }, (_, index) => ({
        ...datasetPreview().records[0],
        record_id: `fixturenews:record-${index + 1}`,
        timestamp: `2026-06-02T${String(index).padStart(2, "0")}:00:00Z`,
        headline: `Preview record ${index + 1}`,
      })),
    });
    const runDataset = vi.fn().mockResolvedValue(preview);

    render(
      <BacktestShellPage
        workspaceId="workspace-alpha"
        now={FIXED_NOW}
        createRun={createRun}
        runDataset={runDataset}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Create draft run" }));
    await screen.findByText("Draft run created");
    fireEvent.click(
      screen.getByRole("button", { name: "Run deterministic BACKTEST dataset" }),
    );

    const table = await screen.findByLabelText("Dataset preview records");
    expect(table.closest(".dataset-preview-table-wrap")).toBeInTheDocument();
    expect(screen.getByText("Preview record 1")).toBeInTheDocument();
    expect(screen.getByText("Preview record 12")).toBeInTheDocument();
  });

  it("downloads JSONL export only after completed dataset generation", async () => {
    const createRun = vi
      .fn()
      .mockImplementation(
        async (_workspaceId: string, request: CreateBacktestRunRequest) =>
          createdRun(request),
      );
    const runDataset = vi.fn().mockResolvedValue(datasetPreview());
    const downloadDatasetExport = vi.fn().mockResolvedValue(undefined);
    render(
      <BacktestShellPage
        workspaceId="workspace-alpha"
        now={FIXED_NOW}
        createRun={createRun}
        runDataset={runDataset}
        downloadDatasetExport={downloadDatasetExport}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Create draft run" }));
    await screen.findByText("Draft run created");
    expect(
      screen.queryByRole("button", { name: "Download JSONL dataset" }),
    ).not.toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "Run deterministic BACKTEST dataset" }),
    );
    await screen.findByText("Completed deterministic dataset");
    fireEvent.click(screen.getByRole("button", { name: "Download JSONL dataset" }));

    expect(downloadDatasetExport).toHaveBeenCalledWith(
      "workspace-alpha",
      "draft-run-001",
    );
    expect(screen.queryByText(/run_id/i)).not.toBeInTheDocument();
  });

  it("disables JSONL export action while download is in progress", async () => {
    const createRun = vi
      .fn()
      .mockImplementation(
        async (_workspaceId: string, request: CreateBacktestRunRequest) =>
          createdRun(request),
      );
    const runDataset = vi.fn().mockResolvedValue(datasetPreview());
    let finishDownload: () => void = () => undefined;
    const downloadDatasetExport = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          finishDownload = resolve;
        }),
    );
    render(
      <BacktestShellPage
        workspaceId="workspace-alpha"
        now={FIXED_NOW}
        createRun={createRun}
        runDataset={runDataset}
        downloadDatasetExport={downloadDatasetExport}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Create draft run" }));
    await screen.findByText("Draft run created");
    fireEvent.click(
      screen.getByRole("button", { name: "Run deterministic BACKTEST dataset" }),
    );
    await screen.findByText("Completed deterministic dataset");
    fireEvent.click(screen.getByRole("button", { name: "Download JSONL dataset" }));

    expect(
      screen.getByRole("button", { name: "Preparing JSONL download..." }),
    ).toBeDisabled();

    finishDownload();
    expect(
      await screen.findByRole("button", { name: "Download JSONL dataset" }),
    ).toBeEnabled();
  });

  it("renders JSONL export errors without displaying export contents", async () => {
    const createRun = vi
      .fn()
      .mockImplementation(
        async (_workspaceId: string, request: CreateBacktestRunRequest) =>
          createdRun(request),
      );
    const runDataset = vi.fn().mockResolvedValue(datasetPreview());
    const downloadDatasetExport = vi
      .fn()
      .mockRejectedValue(new Error("dataset export is not ready"));
    render(
      <BacktestShellPage
        workspaceId="workspace-alpha"
        now={FIXED_NOW}
        createRun={createRun}
        runDataset={runDataset}
        downloadDatasetExport={downloadDatasetExport}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Create draft run" }));
    await screen.findByText("Draft run created");
    fireEvent.click(
      screen.getByRole("button", { name: "Run deterministic BACKTEST dataset" }),
    );
    await screen.findByText("Completed deterministic dataset");
    fireEvent.click(screen.getByRole("button", { name: "Download JSONL dataset" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "dataset export is not ready",
    );
    expect(screen.queryByText(/"run_id"/i)).not.toBeInTheDocument();
  });

  it("displays provider limitation without completed preview records", async () => {
    const createRun = vi
      .fn()
      .mockImplementation(
        async (_workspaceId: string, request: CreateBacktestRunRequest) =>
          createdRun(request),
      );
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
    const providerError = Object.assign(
      new Error(
        "Sharpe Terminal: missing provider configuration: Set SHARPE_API_KEY locally for a BACKTEST smoke check.",
      ),
      { detail: "Sharpe Terminal: missing provider configuration", payload: failedPreview },
    );
    const runDataset = vi.fn().mockRejectedValue(providerError);
    render(
      <BacktestShellPage
        workspaceId="workspace-alpha"
        now={FIXED_NOW}
        createRun={createRun}
        runDataset={runDataset}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Create draft run" }));
    await screen.findByText("Draft run created");
    fireEvent.click(
      screen.getByRole("button", { name: "Run deterministic BACKTEST dataset" }),
    );

    expect(await screen.findByText("Provider limitation")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Sharpe Terminal: missing provider configuration",
    );
    const limitation = screen.getByLabelText("Provider limitation metadata");
    expect(within(limitation).getByText("Sharpe Terminal")).toBeInTheDocument();
    expect(
      within(limitation).getByText("missing provider configuration"),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Dataset preview records")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Download JSONL dataset" }),
    ).not.toBeInTheDocument();
  });

  it("renders API errors", async () => {
    const createRun = vi
      .fn()
      .mockRejectedValue(new Error("BACKTEST timeframe range is invalid"));
    render(
      <BacktestShellPage
        workspaceId="workspace-alpha"
        now={FIXED_NOW}
        createRun={createRun}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Create draft run" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "BACKTEST timeframe range is invalid",
    );
  });

  it("shows client-side timeframe validation feedback", () => {
    const createRun = vi.fn();
    render(
      <BacktestShellPage
        workspaceId="workspace-alpha"
        now={FIXED_NOW}
        createRun={createRun}
      />,
    );

    fireEvent.change(screen.getByLabelText("Timeframe start"), {
      target: { value: "2026-05-01T10:00:00.000Z" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create draft run" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "BACKTEST timeframe range must be no more than 30 days.",
    );
    expect(createRun).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Timeframe start"), {
      target: { value: "2026-06-15T11:00:00.000Z" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create draft run" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Timeframe end must be greater than or equal to timeframe start.",
    );

    fireEvent.change(screen.getByLabelText("Timeframe start"), {
      target: { value: "2026-06-01T10:00:00" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create draft run" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Timeframe values must be timezone-aware ISO timestamps.",
    );
  });

  it("does not use forbidden product-facing wording", () => {
    render(
      <BacktestShellPage
        workspaceId="workspace-alpha"
        now={FIXED_NOW}
        runDataset={async () => datasetPreview()}
      />,
    );

    const visibleText = document.body.textContent ?? "";
    expect(visibleText).not.toMatch(/live/i);
    expect(visibleText).not.toMatch(/broker/i);
    expect(visibleText).not.toMatch(/order/i);
    expect(visibleText).not.toMatch(/investment/i);
    expect(visibleText).not.toMatch(/recommendation/i);
    expect(visibleText).not.toMatch(/signal/i);
  });
});

function datasetPreview(overrides: Partial<DatasetRunPreview> = {}): DatasetRunPreview {
  return {
    summary: {
      workspace_id: "workspace-alpha",
      run_id: "draft-run-001",
      instrument: "BTCUSD",
      mode: "BACKTEST",
      timeframe_start: "2026-06-01T12:00:00.000Z",
      timeframe_end: "2026-06-08T12:00:00.000Z",
      status: "COMPLETED",
      provider_name: "FixtureNews",
      record_count: 2,
      relevant_count: 1,
      noise_count: 1,
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
      {
        workspace_id: "workspace-alpha",
        run_id: "draft-run-001",
        record_id: "fixturenews:record-002",
        timestamp: "2026-06-02T10:00:00Z",
        headline: "Provider placeholder",
        source_id: null,
        source_name: "FixtureNews",
        instrument: "BTCUSD",
        mode: "BACKTEST",
        sentiment_score: 0,
        directional_bias: "FLAT",
        confidence: 0.35,
        relevance: "NOISE",
        model_version: "sentiment-rules-v1",
        config_version: "news-sentiment-policy-v1",
      },
    ],
    ...overrides,
  };
}
