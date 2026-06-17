import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { BacktestRunHistoryPage } from "./BacktestRunHistoryPage";
import type { DatasetRunPreview } from "../backtestShell/types";
import type {
  BacktestRunHistoryItem,
  BacktestRunHistoryResponse,
} from "./types";

describe("BacktestRunHistoryPage", () => {
  it("renders empty workspace history", async () => {
    const loadRunHistory = vi.fn().mockResolvedValue(historyResponse([]));

    render(
      <BacktestRunHistoryPage
        workspaceId="workspace-alpha"
        loadRunHistory={loadRunHistory}
      />,
    );

    expect(
      await screen.findByRole("heading", { name: "BACKTEST run history" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Run history metadata")).toHaveTextContent(
      "workspace-alpha",
    );
    expect(
      await screen.findByText("No BACKTEST runs exist for this workspace yet."),
    ).toBeInTheDocument();
    expect(loadRunHistory).toHaveBeenCalledWith("workspace-alpha");
  });

  it("renders completed run quality and JSONL export controls", async () => {
    const loadRunHistory = vi
      .fn()
      .mockResolvedValue(historyResponse([completedRun()]));
    const downloadDatasetExport = vi.fn().mockResolvedValue(undefined);

    render(
      <BacktestRunHistoryPage
        workspaceId="workspace-alpha"
        loadRunHistory={loadRunHistory}
        downloadDatasetExport={downloadDatasetExport}
      />,
    );

    expect(
      await screen.findByRole("heading", { name: "Config One" }),
    ).toBeInTheDocument();
    const metadata = screen.getByLabelText("draft-run-001 metadata");
    expect(within(metadata).getByText("Sharpe Terminal")).toBeInTheDocument();
    expect(within(metadata).getByText("2")).toBeInTheDocument();
    expect(within(metadata).getByText("sentiment-rules-v1")).toBeInTheDocument();
    expect(within(metadata).getByText("fingerprint-alpha")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open quality report" })).toHaveAttribute(
      "href",
      "/workspaces/workspace-alpha/backtests/draft-run-001/quality",
    );
    expect(
      screen.getByText(/movement fields remain pending price enrichment/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Run deterministic BACKTEST dataset" }),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Download JSONL dataset" }));

    expect(downloadDatasetExport).toHaveBeenCalledWith(
      "workspace-alpha",
      "draft-run-001",
    );
  });

  it("runs deterministic dataset for a draft run and refreshes history", async () => {
    const loadRunHistory = vi
      .fn()
      .mockResolvedValueOnce(historyResponse([draftRun()]))
      .mockResolvedValueOnce(historyResponse([completedRun()]));
    const runDataset = vi.fn().mockResolvedValue(datasetPreview());

    render(
      <BacktestRunHistoryPage
        workspaceId="workspace-alpha"
        loadRunHistory={loadRunHistory}
        runDataset={runDataset}
      />,
    );

    expect(await screen.findByText("No saved configuration")).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Run deterministic BACKTEST dataset" }),
    );

    expect(runDataset).toHaveBeenCalledWith("workspace-alpha", "draft-run-001");
    expect(
      await screen.findByRole("heading", { name: "Config One" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Completed deterministic dataset/i),
    ).toBeInTheDocument();
    expect(loadRunHistory).toHaveBeenCalledTimes(2);
  });

  it("displays provider limitation without completed-run controls", async () => {
    const loadRunHistory = vi
      .fn()
      .mockResolvedValue(historyResponse([providerLimitedRun()]));

    render(
      <BacktestRunHistoryPage
        workspaceId="workspace-alpha"
        loadRunHistory={loadRunHistory}
      />,
    );

    expect(
      await screen.findByText(/Provider limitation is preserved/i),
    ).toBeInTheDocument();
    const limitation = screen.getByLabelText(
      "draft-run-002 provider limitation metadata",
    );
    expect(within(limitation).getByText("Sharpe Terminal")).toBeInTheDocument();
    expect(
      within(limitation).getByText("missing provider configuration"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/does not expose quality or JSONL as completed output/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Open quality report" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Download JSONL dataset" }),
    ).not.toBeInTheDocument();
  });

  it("filters workspace runs by text and status", async () => {
    const loadRunHistory = vi
      .fn()
      .mockResolvedValue(historyResponse([completedRun(), providerLimitedRun()]));

    render(
      <BacktestRunHistoryPage
        workspaceId="workspace-alpha"
        loadRunHistory={loadRunHistory}
      />,
    );

    expect(
      await screen.findByRole("heading", { name: "Config One" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Config Two" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Status"), {
      target: { value: "FAILED_PROVIDER_LIMITATION" },
    });

    expect(screen.queryByRole("heading", { name: "Config One" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Config Two" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Filter runs"), {
      target: { value: "fingerprint-alpha" },
    });

    expect(
      screen.getByText("No BACKTEST runs match the selected filters."),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Status"), {
      target: { value: "ALL" },
    });

    expect(screen.getByRole("heading", { name: "Config One" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Config Two" })).not.toBeInTheDocument();
  });

  it("does not use forbidden product-facing wording", async () => {
    render(
      <BacktestRunHistoryPage
        workspaceId="workspace-alpha"
        loadRunHistory={async () => historyResponse([])}
      />,
    );

    await screen.findByText("No BACKTEST runs exist for this workspace yet.");
    const visibleText = document.body.textContent ?? "";
    expect(visibleText).not.toMatch(/live/i);
    expect(visibleText).not.toMatch(/broker/i);
    expect(visibleText).not.toMatch(/order/i);
    expect(visibleText).not.toMatch(/investment/i);
    expect(visibleText).not.toMatch(/recommendation/i);
    expect(visibleText).not.toMatch(/signal/i);
  });
});

function historyResponse(
  runs: BacktestRunHistoryItem[],
): BacktestRunHistoryResponse {
  return {
    workspace_id: "workspace-alpha",
    runs,
  };
}

function draftRun(
  overrides: Partial<BacktestRunHistoryItem> = {},
): BacktestRunHistoryItem {
  return {
    workspace_id: "workspace-alpha",
    run_id: "draft-run-001",
    config_id: null,
    config_name: null,
    instrument: "BTCUSD",
    mode: "BACKTEST",
    timeframe_start: "2026-06-01T12:00:00.000Z",
    timeframe_end: "2026-06-08T12:00:00.000Z",
    status: "DRAFT",
    created_at: "2026-06-08T12:30:00.000Z",
    dataset_status: null,
    provider_name: null,
    record_count: null,
    relevant_count: null,
    noise_count: null,
    irrelevant_count: null,
    model_version: null,
    config_version: null,
    input_fingerprint: null,
    provider_limitation: null,
    dataset_preview_path: null,
    dataset_export_path: null,
    quality_report_path: null,
    ...overrides,
  };
}

function completedRun(): BacktestRunHistoryItem {
  return draftRun({
    config_id: "config-001",
    config_name: "Config One",
    dataset_status: "COMPLETED",
    provider_name: "Sharpe Terminal",
    record_count: 2,
    relevant_count: 1,
    noise_count: 1,
    irrelevant_count: 0,
    model_version: "sentiment-rules-v1",
    config_version: "news-sentiment-policy-v1",
    input_fingerprint: "fingerprint-alpha",
    dataset_preview_path:
      "/api/workspaces/workspace-alpha/backtests/draft-run-001/dataset",
    dataset_export_path:
      "/api/workspaces/workspace-alpha/backtests/draft-run-001/dataset/export.jsonl",
    quality_report_path:
      "/workspaces/workspace-alpha/backtests/draft-run-001/quality",
  });
}

function providerLimitedRun(): BacktestRunHistoryItem {
  return draftRun({
    run_id: "draft-run-002",
    config_id: "config-002",
    config_name: "Config Two",
    dataset_status: "FAILED_PROVIDER_LIMITATION",
    provider_name: "Sharpe Terminal",
    record_count: 0,
    relevant_count: 0,
    noise_count: 0,
    irrelevant_count: 0,
    model_version: "sentiment-rules-v1",
    config_version: "news-sentiment-policy-v1",
    input_fingerprint: "fingerprint-beta",
    provider_limitation: {
      provider_name: "Sharpe Terminal",
      reason: "missing provider configuration",
      detail: "Set SHARPE_API_KEY locally for a BACKTEST smoke check.",
    },
    dataset_preview_path:
      "/api/workspaces/workspace-alpha/backtests/draft-run-002/dataset",
  });
}

function datasetPreview(): DatasetRunPreview {
  return {
    summary: {
      workspace_id: "workspace-alpha",
      run_id: "draft-run-001",
      instrument: "BTCUSD",
      mode: "BACKTEST",
      timeframe_start: "2026-06-01T12:00:00.000Z",
      timeframe_end: "2026-06-08T12:00:00.000Z",
      status: "COMPLETED",
      provider_name: "Sharpe Terminal",
      record_count: 2,
      relevant_count: 1,
      noise_count: 1,
      irrelevant_count: 0,
      model_version: "sentiment-rules-v1",
      config_version: "news-sentiment-policy-v1",
      input_fingerprint: "fingerprint-alpha",
      provider_limitation: null,
    },
    records: [],
  };
}
