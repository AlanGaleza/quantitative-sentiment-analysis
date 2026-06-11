import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SentimentReturnPlot } from "./SentimentReturnPlot";
import type { QualityChartPoint } from "./types";

const points: QualityChartPoint[] = [
  {
    event_timestamp: "2026-06-08T12:01:00Z",
    sentiment_score: 0.8,
    later_return: 0.04,
    directional_bias: "LONG",
    realized_direction: "UP",
    confidence: 0.75,
    outcome: "HIT",
  },
  {
    event_timestamp: "2026-06-08T12:02:00Z",
    sentiment_score: -0.6,
    later_return: -0.03,
    directional_bias: "SHORT",
    realized_direction: "DOWN",
    confidence: 0.75,
    outcome: "MISS",
  },
  {
    event_timestamp: "2026-06-08T12:03:00Z",
    sentiment_score: 0.5,
    later_return: null,
    directional_bias: "LONG",
    realized_direction: null,
    confidence: 0.75,
    outcome: "MISS",
  },
];

describe("SentimentReturnPlot", () => {
  it("renders accessible chart point outcomes", () => {
    render(<SentimentReturnPlot points={points} />);

    expect(
      screen.getByRole("img", {
        name: "Sentiment versus later BTCUSD return plot",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Point 1: LONG directional bias, later return 4.00%, HIT"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Point 2: SHORT directional bias, later return -3.00%, MISS"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Point 3: LONG directional bias, later return missing, MISS"),
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
