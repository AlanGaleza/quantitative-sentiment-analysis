import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SentimentReturnPlot } from "./SentimentReturnPlot";
import { backtestQualityReport } from "./testFixtures";

describe("SentimentReturnPlot", () => {
  it("renders accessible chart point outcomes", () => {
    render(<SentimentReturnPlot points={backtestQualityReport.chart_points} />);

    expect(
      screen.getByRole("img", {
        name: "Sentiment versus later BTCUSD return plot",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Point 1: LONG directional bias, later return 4.00%, HIT"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Point 2: SHORT directional bias, later return -3.00%, HIT"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Point 4: LONG directional bias, later return missing, MISS"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Chart points may be a deterministic sample of the full BACKTEST report; metrics above use the report denominator.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("1 chart point missing numeric later return.")).toBeInTheDocument();
  });

  it("renders an empty state without chart markers", () => {
    render(<SentimentReturnPlot points={[]} />);

    expect(
      screen.getByText("No chart points are available for this BACKTEST report."),
    ).toBeInTheDocument();
  });
});
