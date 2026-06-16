import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SentimentReturnPlot } from "./SentimentReturnPlot";
import {
  backtestQualityReport,
  emptyBacktestQualityReport,
  enrichedBacktestQualityReport,
  zeroNumericBacktestQualityReport,
} from "./testFixtures";

describe("SentimentReturnPlot", () => {
  it("renders an empty report state without chart markers", () => {
    render(<SentimentReturnPlot points={emptyBacktestQualityReport.chart_points} />);

    expect(
      screen.getByText("No chart points are available for this BACKTEST report."),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("img", {
        name: "Sentiment versus later BTCUSD return plot",
      }),
    ).not.toBeInTheDocument();
  });

  it("renders a no numeric pairs state without SVG axes", () => {
    render(
      <SentimentReturnPlot points={zeroNumericBacktestQualityReport.chart_points} />,
    );

    expect(screen.getByText("0 numeric pairs")).toBeInTheDocument();
    expect(
      screen.getByText(/No numeric later return pairs are available/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/2 chart points missing numeric later return/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("img", {
        name: "Sentiment versus later BTCUSD return plot",
      }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText("Point 1: LONG directional bias, later return missing, MISS"),
    ).toBeInTheDocument();
  });

  it("renders mixed numeric and missing chart point outcomes", () => {
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

  it("renders all numeric reports without a missing movement summary", () => {
    render(<SentimentReturnPlot points={enrichedBacktestQualityReport.chart_points} />);

    expect(
      screen.getByRole("img", {
        name: "Sentiment versus later BTCUSD return plot",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("5 numeric pairs")).toBeInTheDocument();
    expect(screen.getByText("0 chart points missing numeric later return.")).toBeInTheDocument();
  });
});
