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
const SENTIMENT_TICKS = [-1, -0.5, 0, 0.5, 1];
const RETURN_TICK_COUNT = 5;

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

  if (numericPoints.length === 0) {
    return (
      <section className="plot-panel" aria-labelledby="plot-heading">
        <div className="section-heading">
          <h2 id="plot-heading">Sentiment vs later BTCUSD return</h2>
          <span>0 numeric pairs</span>
        </div>
        <p role="status" className="empty-state plot-empty-state">
          No numeric later return pairs are available for the selected BACKTEST
          horizon. {missingPoints.length} chart point
          {missingPoints.length === 1 ? "" : "s"} missing numeric later return.
        </p>
        <ul aria-label="Chart point outcomes">
          {points.map((point, index) => (
            <li key={`${point.event_timestamp}-${index}`}>
              {pointLabel(point, index)}
            </li>
          ))}
        </ul>
      </section>
    );
  }

  const returnDomain = buildReturnDomain(numericPoints.map((point) => point.later_return));
  const plottedPoints: NumericPoint[] = numericPoints.map((point) => ({
    point,
    x: scaleSentiment(point.sentiment_score),
    y: scaleReturn(point.later_return, returnDomain),
  }));
  const returnTicks = buildReturnTicks(returnDomain);

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
        {returnTicks.map((tick) => {
          const y = scaleReturn(tick, returnDomain);
          return (
            <g key={`return-tick-${tick}`}>
              <line
                x1={PADDING}
                y1={y}
                x2={WIDTH - PADDING}
                y2={y}
                className={isZeroTick(tick) ? "axis-line axis-zero" : "axis-grid"}
              />
              <text x={PADDING - 10} y={y + 4} className="axis-value" textAnchor="end">
                {formatAxisReturn(tick)}
              </text>
            </g>
          );
        })}
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
        {SENTIMENT_TICKS.map((tick) => {
          const x = scaleSentiment(tick);
          return (
            <g key={`sentiment-tick-${tick}`}>
              <line
                x1={x}
                y1={HEIGHT - PADDING}
                x2={x}
                y2={HEIGHT - PADDING + 6}
                className="axis-tick"
              />
              <text x={x} y={HEIGHT - PADDING + 22} className="axis-value" textAnchor="middle">
                {formatAxisSentiment(tick)}
              </text>
            </g>
          );
        })}
        <text x={WIDTH / 2} y={HEIGHT - 10} className="axis-label" textAnchor="middle">
          sentiment score
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

      <ul className="plot-legend" aria-label="Plot legend">
        <li>
          <span className="legend-swatch plot-dot-hit" aria-hidden="true" />
          HIT
        </li>
        <li>
          <span className="legend-swatch plot-dot-miss" aria-hidden="true" />
          MISS
        </li>
        <li>
          <span className="legend-swatch plot-dot-excluded" aria-hidden="true" />
          EXCLUDED
        </li>
      </ul>

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

function buildReturnTicks([min, max]: [number, number]): number[] {
  if (min === max) {
    return [min];
  }
  if (min < 0 && max > 0) {
    return [min, min / 2, 0, max / 2, max];
  }

  const step = (max - min) / (RETURN_TICK_COUNT - 1);
  return Array.from({ length: RETURN_TICK_COUNT }, (_, index) => min + step * index);
}

function scaleSentiment(value: number): number {
  return PADDING + ((value + 1) / 2) * (WIDTH - PADDING * 2);
}

function scaleReturn(value: number, [min, max]: [number, number]): number {
  return HEIGHT - PADDING - ((value - min) / (max - min)) * (HEIGHT - PADDING * 2);
}

function isZeroTick(value: number): boolean {
  return Math.abs(value) < 0.0000001;
}

function formatAxisSentiment(value: number): string {
  if (value > 0) {
    return `+${value}`;
  }
  return `${value}`;
}

function formatAxisReturn(value: number): string {
  if (isZeroTick(value)) {
    return "0.00%";
  }
  return `${(value * 100).toFixed(2)}%`;
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
