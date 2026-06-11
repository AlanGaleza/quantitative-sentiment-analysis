import { useEffect, useState } from "react";

import {
  fetchBacktestQualityReport,
  type QualityReportApiError,
} from "./api";
import { SentimentReturnPlot } from "./SentimentReturnPlot";
import type { BacktestQualityReport, QualityInputRecord } from "./types";

type ReportLoader = (
  workspaceId: string,
  runId: string,
) => Promise<BacktestQualityReport>;

interface BacktestQualityPageProps {
  workspaceId: string;
  runId: string;
  loadReport?: ReportLoader;
}

type LoadState =
  | { status: "loading" }
  | { status: "loaded"; report: BacktestQualityReport }
  | { status: "error"; message: string };

export function BacktestQualityPage({
  workspaceId,
  runId,
  loadReport = fetchBacktestQualityReport,
}: BacktestQualityPageProps) {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let isCurrent = true;
    setState({ status: "loading" });

    loadReport(workspaceId, runId)
      .then((report) => {
        if (isCurrent) {
          setState({ status: "loaded", report });
        }
      })
      .catch((error: QualityReportApiError | Error) => {
        if (isCurrent) {
          setState({ status: "error", message: error.message });
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [loadReport, runId, workspaceId]);

  if (state.status === "loading") {
    return (
      <main className="quality-page">
        <Header workspaceId={workspaceId} runId={runId} />
        <p role="status" className="loading-state">
          Loading BACKTEST quality report...
        </p>
      </main>
    );
  }

  if (state.status === "error") {
    return (
      <main className="quality-page">
        <Header workspaceId={workspaceId} runId={runId} />
        <div role="alert" className="error-state">
          {state.message}
        </div>
      </main>
    );
  }

  return (
    <main className="quality-page">
      <Header workspaceId={workspaceId} runId={runId} report={state.report} />
      <MetricGrid report={state.report} />
      <Warnings warnings={state.report.warnings} />
      <SentimentReturnPlot points={state.report.chart_points} />
      <RecordsTable records={state.report.representative_records} />
    </main>
  );
}

function Header({
  workspaceId,
  runId,
  report,
}: {
  workspaceId: string;
  runId: string;
  report?: BacktestQualityReport;
}) {
  return (
    <header className="quality-header">
      <div>
        <p className="eyebrow">BTCUSD BACKTEST</p>
        <h1>Backtest quality report</h1>
        <p className="safety-copy">
          BACKTEST-only analytical dataset quality indicator for historical
          BTCUSD evaluation. This view evaluates directional bias quality only.
        </p>
      </div>
      <dl className="metadata-grid" aria-label="Report metadata">
        <MetadataItem label="Workspace" value={report?.workspace_id ?? workspaceId} />
        <MetadataItem label="Run" value={report?.run_id ?? runId} />
        <MetadataItem label="Instrument" value={report?.instrument ?? "BTCUSD"} />
        <MetadataItem label="Mode" value={report?.mode ?? "BACKTEST"} />
        {report ? (
          <>
            <MetadataItem
              label="Horizon"
              value={`${report.horizon.value} ${report.horizon.unit}`}
            />
            <MetadataItem label="Model" value={report.model_version} />
            <MetadataItem label="Config" value={report.config_version} />
          </>
        ) : null}
      </dl>
    </header>
  );
}

function MetadataItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function MetricGrid({ report }: { report: BacktestQualityReport }) {
  const { metrics } = report;
  const metricsList = [
    {
      label: "Hit rate",
      value: formatPercent(metrics.hit_rate),
      detail: `${metrics.hit_count}/${metrics.sample_count} non-noise records`,
    },
    {
      label: "Correlation",
      value: formatNullableNumber(metrics.correlation),
      detail: `${metrics.correlation_pair_count} numeric pairs`,
    },
    {
      label: "Missing movement counted as miss",
      value: String(metrics.missing_movement_count),
      detail: `${metrics.miss_count} total misses`,
    },
    {
      label: "Noise preserved",
      value: String(metrics.noise_count),
      detail: "excluded from metric denominators",
    },
    {
      label: "FLAT rows",
      value: String(metrics.flat_count),
      detail: "hit only against realized FLAT movement",
    },
  ];

  return (
    <section className="metric-grid" aria-label="Quality metrics">
      {metricsList.map((metric) => (
        <article className="metric-card" key={metric.label}>
          <h2>{metric.label}</h2>
          <p className="metric-value">{metric.value}</p>
          <p>{metric.detail}</p>
        </article>
      ))}
    </section>
  );
}

function Warnings({ warnings }: { warnings: string[] }) {
  return (
    <section className="warnings-panel" aria-labelledby="warnings-heading">
      <div className="section-heading">
        <h2 id="warnings-heading">Report warnings</h2>
        <span>{warnings.length}</span>
      </div>
      {warnings.length === 0 ? (
        <p>No warnings for this BACKTEST report.</p>
      ) : (
        <ul>
          {warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

function RecordsTable({ records }: { records: QualityInputRecord[] }) {
  return (
    <section className="records-panel" aria-labelledby="records-heading">
      <div className="section-heading">
        <h2 id="records-heading">Representative records</h2>
        <span>{records.length}</span>
      </div>
      {records.length === 0 ? (
        <p role="status" className="empty-state">
          No representative records are available for this BACKTEST report.
        </p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Headline</th>
                <th>Source</th>
                <th>Sentiment</th>
                <th>Directional bias</th>
                <th>Later return</th>
                <th>Realized</th>
                <th>Relevance</th>
              </tr>
            </thead>
            <tbody>
              {records.map((record) => (
                <tr key={record.record_id ?? `${record.event_timestamp}-${record.headline}`}>
                  <td>{formatTimestamp(record.event_timestamp)}</td>
                  <td>{record.headline}</td>
                  <td>{record.source_name ?? record.source_id}</td>
                  <td>{record.sentiment_score.toFixed(2)}</td>
                  <td>{record.directional_bias}</td>
                  <td>{formatReturn(record.later_return)}</td>
                  <td>{record.realized_direction ?? "missing"}</td>
                  <td>{record.relevance}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function formatPercent(value: number | null): string {
  if (value === null) {
    return "n/a";
  }

  return `${(value * 100).toFixed(1)}%`;
}

function formatNullableNumber(value: number | null): string {
  if (value === null) {
    return "n/a";
  }

  return value.toFixed(3);
}

function formatReturn(value: number | null): string {
  if (value === null) {
    return "missing";
  }

  return `${(value * 100).toFixed(2)}%`;
}

function formatTimestamp(value: string): string {
  return new Date(value).toISOString().replace(".000Z", "Z");
}
