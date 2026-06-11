import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { BacktestQualityPage } from "./BacktestQualityPage";
import {
  backtestQualityReport,
  emptyBacktestQualityReport,
} from "./testFixtures";

describe("BacktestQualityPage", () => {
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
    expect(loadReport).toHaveBeenCalledWith("workspace-alpha", "run-001");
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

    expect(screen.getByText("4 hours")).toBeInTheDocument();
    expect(screen.getByText("sentiment-rules-v1")).toBeInTheDocument();
    expect(screen.getByText("quality-config-v1")).toBeInTheDocument();
    expect(screen.getByText("BTCUSD quality fixture with missing movement")).toBeInTheDocument();
    expect(screen.getAllByText("missing").length).toBeGreaterThan(0);
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
