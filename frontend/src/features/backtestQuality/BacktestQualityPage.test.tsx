import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { BacktestQualityPage } from "./BacktestQualityPage";
import {
  backtestQualityReport,
  emptyBacktestQualityReport,
} from "./testFixtures";

describe("BacktestQualityPage", () => {
  afterEach(() => {
    window.history.pushState({}, "", "/");
  });

  it("renders the report contract without recalculating metrics", async () => {
    const loadReport = vi.fn().mockResolvedValue(backtestQualityReport);

    render(
      <BacktestQualityPage
        workspaceId="workspace-alpha"
        runId="run-001"
        loadReport={loadReport}
      />,
    );

    expect(
      await screen.findByRole("heading", { name: "Backtest quality report" }),
    ).toBeInTheDocument();
    expect(loadReport).toHaveBeenCalledWith(
      "workspace-alpha",
      "run-001",
      expect.objectContaining({ value: 4, unit: "hours" }),
    );
    expect(screen.getByLabelText("Quality horizon")).toHaveValue("4-hours");
    expect(screen.getByText("BACKTEST-only analytical dataset quality indicator", {
      exact: false,
    })).toBeInTheDocument();
    expect(screen.queryByText(/recommendation/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/signal/i)).not.toBeInTheDocument();

    const metrics = screen.getByLabelText("Quality metrics");
    expect(within(metrics).getByText("75.0%")).toBeInTheDocument();
    expect(within(metrics).getByText("0.997")).toBeInTheDocument();
    expect(within(metrics).getByText("Missing movement counted as miss")).toBeInTheDocument();
    expect(within(metrics).getByText("1 total misses")).toBeInTheDocument();

    const metadata = screen.getByLabelText("Report metadata");
    expect(within(metadata).getByText("4 hours")).toBeInTheDocument();
    expect(screen.getByText("sentiment-rules-v1")).toBeInTheDocument();
    expect(screen.getByText("quality-config-v1")).toBeInTheDocument();
    expect(screen.getByText("BTCUSD quality fixture with missing movement")).toBeInTheDocument();
    expect(screen.getAllByText("missing").length).toBeGreaterThan(0);
    expect(screen.getByText(/counted as misses/i)).toBeInTheDocument();
  });

  it("loads a selected horizon from URL state", async () => {
    window.history.pushState(
      {},
      "",
      "/workspaces/workspace-alpha/backtests/run-001/quality?horizon_value=1&horizon_unit=minutes",
    );
    const loadReport = vi.fn().mockResolvedValue({
      ...backtestQualityReport,
      horizon: { value: 1, unit: "minutes" },
    });

    render(
      <BacktestQualityPage
        workspaceId="workspace-alpha"
        runId="run-001"
        loadReport={loadReport}
      />,
    );

    await screen.findByRole("heading", { name: "Backtest quality report" });
    const metadata = screen.getByLabelText("Report metadata");
    expect(within(metadata).getByText("1 minute")).toBeInTheDocument();
    expect(screen.getByLabelText("Quality horizon")).toHaveValue("1-minutes");
    expect(loadReport).toHaveBeenCalledWith(
      "workspace-alpha",
      "run-001",
      expect.objectContaining({ value: 1, unit: "minutes" }),
    );
  });

  it("changes to 1 minute horizon through URL-backed state", async () => {
    window.history.pushState(
      {},
      "",
      "/workspaces/workspace-alpha/backtests/run-001/quality",
    );
    const oneMinuteReport = {
      ...backtestQualityReport,
      horizon: { value: 1, unit: "minutes" as const },
    };
    const loadReport = vi.fn(
      async (
        _workspaceId: string,
        _runId: string,
        horizon = { value: 4, unit: "hours" as const },
      ) => (horizon.value === 1 ? oneMinuteReport : backtestQualityReport),
    );

    render(
      <BacktestQualityPage
        workspaceId="workspace-alpha"
        runId="run-001"
        loadReport={loadReport}
      />,
    );

    await screen.findByRole("heading", { name: "Backtest quality report" });
    expect(
      within(screen.getByLabelText("Report metadata")).getByText("4 hours"),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Quality horizon"), {
      target: { value: "1-minutes" },
    });

    await waitFor(() => {
      expect(loadReport).toHaveBeenLastCalledWith(
        "workspace-alpha",
        "run-001",
        expect.objectContaining({ value: 1, unit: "minutes" }),
      );
    });
    expect(window.location.search).toBe(
      "?horizon_value=1&horizon_unit=minutes",
    );
    expect(
      within(screen.getByLabelText("Report metadata")).getByText("1 minute"),
    ).toBeInTheDocument();
    expect(screen.getByText(/counted as misses/i)).toBeInTheDocument();
  });

  it("renders API errors", async () => {
    const loadReport = vi.fn().mockRejectedValue(
      new Error("S-02 deterministic completed-run storage is not integrated yet"),
    );

    render(
      <BacktestQualityPage
        workspaceId="workspace-alpha"
        runId="run-001"
        loadReport={loadReport}
      />,
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "S-02 deterministic completed-run storage is not integrated yet",
    );
  });

  it("renders empty report sections", async () => {
    const loadReport = vi.fn().mockResolvedValue(emptyBacktestQualityReport);

    render(
      <BacktestQualityPage
        workspaceId="workspace-alpha"
        runId="run-001"
        loadReport={loadReport}
      />,
    );

    expect(await screen.findByText("No warnings for this BACKTEST report.")).toBeInTheDocument();
    expect(
      screen.getByText("No chart points are available for this BACKTEST report."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("No representative records are available for this BACKTEST report."),
    ).toBeInTheDocument();
  });
});
