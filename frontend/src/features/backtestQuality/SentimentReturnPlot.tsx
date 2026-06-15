import type { QualityChartPoint } from "./types";

interface SentimentReturnPlotProps {
  points: QualityChartPoint[];
}

interface NumericPoint {
  point: QualityChartPoint;
  x: number;
  y: number;
}

const WIDTH = 720;
const HEIGHT = 320;
const PADDING = 48;

export function SentimentReturnPlot({ points }: SentimentReturnPlotProps) {
  if (points.length === 0) {
    return (
      <section className="plot-panel" aria-labelledby="plot-heading">
        <h2 id="plot-heading">Sentiment vs later BTCUSD return</h2>
        <p role="status" className="empty-state">
          No chart points are available for this BACKTEST report.
        </p>
      </section>
    );
  }

  const numericPoints = points.filter(
    (point) => point.later_return !== null,
  ) as Array<QualityChartPoint & { later_return: number }>;
  const missingPoints = points.filter((point) => point.later_return === null);
  const returnDomain = buildReturnDomain(numericPoints.map((point) => point.later_return));
  const plottedPoints: NumericPoint[] = numericPoints.map((point) => ({
    point,
    x: scaleSentiment(point.sentiment_score),
    y: scaleReturn(point.later_return, returnDomain),
  }));
  const zeroY = scaleReturn(0, returnDomain);

  return (
    <section className="plot-panel" aria-labelledby="plot-heading">
      <div className="section-heading">
        <h2 id="plot-heading">Sentiment vs later BTCUSD return</h2>
        <span>{numericPoints.length} numeric pairs</span>
      </div>

      <svg
        className="plot-svg"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label="Sentiment versus later BTCUSD return plot"
      >
        <line
          x1={PADDING}
          y1={zeroY}
          x2={WIDTH - PADDING}
          y2={zeroY}
          className="axis-line axis-zero"
        />
        <line
          x1={PADDING}
          y1={PADDING}
          x2={PADDING}
          y2={HEIGHT - PADDING}
          className="axis-line"
        />
        <line
          x1={PADDING}
          y1={HEIGHT - PADDING}
          x2={WIDTH - PADDING}
          y2={HEIGHT - PADDING}
          className="axis-line"
        />
        <text x={PADDING} y={HEIGHT - 14} className="axis-label">
          -1 sentiment
        </text>
        <text x={WIDTH - PADDING - 90} y={HEIGHT - 14} className="axis-label">
          +1 sentiment
        </text>
        <text x={12} y={PADDING - 18} className="axis-label">
          later return
        </text>

        {plottedPoints.map(({ point, x, y }, index) => (
          <g key={`${point.event_timestamp}-${index}`}>
            <circle
              cx={x}
              cy={y}
              r="8"
              className={`plot-dot plot-dot-${point.outcome.toLowerCase()}`}
            />
          </g>
        ))}
      </svg>

      <div className="plot-summary">
        <p>
          Chart points may be a deterministic sample of the full BACKTEST report;
          metrics above use the report denominator.
        </p>
        <p>
          {missingPoints.length} chart point
          {missingPoints.length === 1 ? "" : "s"} missing numeric later return.
        </p>
        <ul aria-label="Chart point outcomes">
          {points.map((point, index) => (
            <li key={`${point.event_timestamp}-${index}`}>
              {pointLabel(point, index)}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function buildReturnDomain(values: number[]): [number, number] {
  if (values.length === 0) {
    return [-0.01, 0.01];
  }

  let min = 0;
  let max = 0;
  for (const value of values) {
    min = Math.min(min, value);
    max = Math.max(max, value);
  }
  if (min === max) {
    return [min - 0.01, max + 0.01];
  }

  const padding = (max - min) * 0.12;
  return [min - padding, max + padding];
}

function scaleSentiment(value: number): number {
  return PADDING + ((value + 1) / 2) * (WIDTH - PADDING * 2);
}

function scaleReturn(value: number, [min, max]: [number, number]): number {
  return HEIGHT - PADDING - ((value - min) / (max - min)) * (HEIGHT - PADDING * 2);
}

function pointLabel(point: QualityChartPoint, index: number): string {
  return `Point ${index + 1}: ${point.directional_bias} directional bias, later return ${formatReturn(
    point.later_return,
  )}, ${point.outcome}`;
}

function formatReturn(value: number | null): string {
  if (value === null) {
    return "missing";
  }

  return `${(value * 100).toFixed(2)}%`;
}
