import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { BacktestShellPage } from "./BacktestShellPage";
import type { BacktestRunShell, CreateBacktestRunRequest } from "./types";

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
      screen.getByText(/unavailable until S-02 produces a completed deterministic dataset/i),
    ).toBeInTheDocument();
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
    render(<BacktestShellPage workspaceId="workspace-alpha" now={FIXED_NOW} />);

    const visibleText = document.body.textContent ?? "";
    expect(visibleText).not.toMatch(/live/i);
    expect(visibleText).not.toMatch(/broker/i);
    expect(visibleText).not.toMatch(/order/i);
    expect(visibleText).not.toMatch(/investment/i);
    expect(visibleText).not.toMatch(/recommendation/i);
    expect(visibleText).not.toMatch(/signal/i);
  });
});
