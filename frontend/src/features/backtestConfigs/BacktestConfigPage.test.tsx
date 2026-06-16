import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { BacktestConfigPage } from "./BacktestConfigPage";
import type { BacktestConfig } from "./api";
import type {
  BacktestRunShell,
  CreateBacktestRunRequest,
  DatasetRunPreview,
} from "../backtestShell/types";

const FIXED_NOW = new Date("2026-06-15T10:00:00.000Z");
const DEFAULT_START = "2026-05-16T10:00:00.000Z";
const DEFAULT_END = "2026-06-15T10:00:00.000Z";

describe("BacktestConfigPage", () => {
  it("loads saved BACKTEST configurations for a workspace", async () => {
    render(
      <BacktestConfigPage
        workspaceId="workspace-alpha"
        now={FIXED_NOW}
        loadConfigs={async () => [configResponse()]}
      />,
    );

    expect(
      await screen.findByRole("heading", {
        name: "Saved BACKTEST configurations",
      }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Configuration name")).toHaveValue("");
    expect(screen.getByLabelText("Timeframe start")).toHaveValue(DEFAULT_START);
    expect(screen.getByLabelText("Timeframe end")).toHaveValue(DEFAULT_END);
    expect(screen.getByRole("heading", { name: "Baseline BTC config" })).toBeInTheDocument();
    const metadata = screen.getByLabelText("Baseline BTC config metadata");
    expect(within(metadata).getByText("BTCUSD")).toBeInTheDocument();
    expect(within(metadata).getByText("2026-06-01T12:00:00.000Z")).toBeInTheDocument();
  });

  it("creates, edits, and deletes a saved configuration", async () => {
    const createConfig = vi.fn().mockResolvedValue(configResponse());
    const updateConfig = vi.fn().mockResolvedValue(
      configResponse({
        name: "Renamed config",
        updated_at: "2026-06-08T12:45:00.000Z",
      }),
    );
    const removeConfig = vi.fn().mockResolvedValue(undefined);
    render(
      <BacktestConfigPage
        workspaceId="workspace-alpha"
        now={FIXED_NOW}
        loadConfigs={async () => []}
        createConfig={createConfig}
        updateConfig={updateConfig}
        removeConfig={removeConfig}
      />,
    );

    await screen.findByText("No saved BACKTEST configurations exist for this workspace.");
    fireEvent.change(screen.getByLabelText("Configuration name"), {
      target: { value: "  Baseline BTC config  " },
    });
    fireEvent.change(screen.getByLabelText("Timeframe start"), {
      target: { value: "2026-06-01T12:00:00.000Z" },
    });
    fireEvent.change(screen.getByLabelText("Timeframe end"), {
      target: { value: "2026-06-08T12:00:00.000Z" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create configuration" }));

    expect(await screen.findByRole("heading", { name: "Baseline BTC config" })).toBeInTheDocument();
    expect(createConfig).toHaveBeenCalledWith("workspace-alpha", {
      name: "Baseline BTC config",
      instrument: "BTCUSD",
      mode: "BACKTEST",
      timeframe_start: "2026-06-01T12:00:00.000Z",
      timeframe_end: "2026-06-08T12:00:00.000Z",
    });

    fireEvent.click(screen.getByRole("button", { name: "Edit Baseline BTC config" }));
    expect(screen.getByLabelText("Configuration name")).toHaveValue(
      "Baseline BTC config",
    );
    fireEvent.change(screen.getByLabelText("Configuration name"), {
      target: { value: "Renamed config" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save configuration" }));

    expect(await screen.findByRole("heading", { name: "Renamed config" })).toBeInTheDocument();
    expect(updateConfig).toHaveBeenCalledWith(
      "workspace-alpha",
      "config-001",
      {
        name: "Renamed config",
        instrument: "BTCUSD",
        mode: "BACKTEST",
        timeframe_start: "2026-06-01T12:00:00.000Z",
        timeframe_end: "2026-06-08T12:00:00.000Z",
      },
    );

    fireEvent.click(screen.getByRole("button", { name: "Delete Renamed config" }));
    expect(
      screen.getByRole("button", { name: "Confirm delete Renamed config" }),
    ).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Confirm delete Renamed config" }),
    );

    expect(
      await screen.findByText(
        "No saved BACKTEST configurations exist for this workspace.",
      ),
    ).toBeInTheDocument();
    expect(removeConfig).toHaveBeenCalledWith("workspace-alpha", "config-001");
  });

  it("creates a draft from config and can run dataset plus JSONL export", async () => {
    const createDraft = vi.fn().mockResolvedValue(draftRun());
    const runDataset = vi.fn().mockResolvedValue(datasetPreview());
    const downloadDatasetExport = vi.fn().mockResolvedValue(undefined);
    render(
      <BacktestConfigPage
        workspaceId="workspace-alpha"
        now={FIXED_NOW}
        loadConfigs={async () => [configResponse()]}
        createDraft={createDraft}
        runDataset={runDataset}
        downloadDatasetExport={downloadDatasetExport}
      />,
    );

    await screen.findByRole("heading", { name: "Baseline BTC config" });
    fireEvent.click(
      screen.getByRole("button", {
        name: "Create draft run from Baseline BTC config",
      }),
    );

    expect(await screen.findByText("Draft run from saved configuration")).toBeInTheDocument();
    expect(createDraft).toHaveBeenCalledWith("workspace-alpha", "config-001");

    fireEvent.click(
      screen.getByRole("button", { name: "Run deterministic BACKTEST dataset" }),
    );
    expect(
      await screen.findByText("Completed deterministic dataset"),
    ).toBeInTheDocument();
    expect(runDataset).toHaveBeenCalledWith("workspace-alpha", "draft-run-001");
    expect(screen.getByRole("link", { name: "Quality route" })).toHaveAttribute(
      "href",
      "/workspaces/workspace-alpha/backtests/draft-run-001/quality",
    );

    fireEvent.click(screen.getByRole("button", { name: "Download JSONL dataset" }));
    expect(downloadDatasetExport).toHaveBeenCalledWith(
      "workspace-alpha",
      "draft-run-001",
    );
  });

  it("shows client-side validation feedback", async () => {
    const createConfig = vi.fn();
    render(
      <BacktestConfigPage
        workspaceId="workspace-alpha"
        now={FIXED_NOW}
        loadConfigs={async () => []}
        createConfig={createConfig}
      />,
    );

    await screen.findByText("No saved BACKTEST configurations exist for this workspace.");
    fireEvent.click(screen.getByRole("button", { name: "Create configuration" }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Configuration name is required.",
    );

    fireEvent.change(screen.getByLabelText("Configuration name"), {
      target: { value: "Long range config" },
    });
    fireEvent.change(screen.getByLabelText("Timeframe start"), {
      target: { value: "2026-05-01T10:00:00.000Z" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create configuration" }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "BACKTEST timeframe range must be no more than 30 days.",
    );
    expect(createConfig).not.toHaveBeenCalled();
  });
});

function configResponse(overrides: Partial<BacktestConfig> = {}): BacktestConfig {
  return {
    id: "config-001",
    workspace_id: "workspace-alpha",
    name: "Baseline BTC config",
    instrument: "BTCUSD",
    mode: "BACKTEST",
    timeframe_start: "2026-06-01T12:00:00.000Z",
    timeframe_end: "2026-06-08T12:00:00.000Z",
    created_at: "2026-06-08T12:30:00.000Z",
    updated_at: "2026-06-08T12:30:00.000Z",
    ...overrides,
  };
}

function draftRun(
  request: CreateBacktestRunRequest = {
    instrument: "BTCUSD",
    mode: "BACKTEST",
    timeframe_start: "2026-06-01T12:00:00.000Z",
    timeframe_end: "2026-06-08T12:00:00.000Z",
  },
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
    created_at: "2026-06-08T12:30:00.000Z",
    quality_report_path:
      "/workspaces/workspace-alpha/backtests/draft-run-001/quality",
    ...overrides,
  };
}

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
      record_count: 1,
      relevant_count: 1,
      noise_count: 0,
      irrelevant_count: 0,
      model_version: "sentiment-rules-v1",
      config_version: "news-sentiment-policy-v1",
      input_fingerprint: "fingerprint-alpha",
      provider_limitation: null,
    },
    records: [],
    ...overrides,
  };
}
