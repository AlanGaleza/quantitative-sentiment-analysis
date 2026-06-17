import { useEffect, useState } from "react";

import {
  fetchBacktestQualityReport,
  type QualityReportApiError,
} from "./api";
import { SentimentReturnPlot } from "./SentimentReturnPlot";
import {
  DEFAULT_QUALITY_HORIZON,
  SUPPORTED_QUALITY_HORIZONS,
  type BacktestQualityReport,
  type DirectionalBias,
  type HorizonUnit,
  type QualityHorizon,
  type QualityInputRecord,
  type RelevanceLabel,
  type SupportedQualityHorizon,
} from "./types";

type ReportLoader = (
  workspaceId: string,
  runId: string,
  horizon?: QualityHorizon,
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
  const [selectedHorizon, setSelectedHorizon] = useState<SupportedQualityHorizon>(
    () => horizonFromSearch(window.location.search),
  );

  useEffect(() => {
    let isCurrent = true;
    setState({ status: "loading" });

    loadReport(workspaceId, runId, selectedHorizon)
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
  }, [
    loadReport,
    runId,
    selectedHorizon,
    selectedHorizon.unit,
    selectedHorizon.value,
    workspaceId,
  ]);

  useEffect(() => {
    function handlePopState() {
      setSelectedHorizon(horizonFromSearch(window.location.search));
    }

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  function handleHorizonChange(nextHorizon: SupportedQualityHorizon) {
    setSelectedHorizon(nextHorizon);
    updateUrlHorizon(nextHorizon);
  }

  if (state.status === "loading") {
    return (
      <main className="quality-page">
        <Header
          workspaceId={workspaceId}
          runId={runId}
          selectedHorizon={selectedHorizon}
          onHorizonChange={handleHorizonChange}
        />
        <p role="status" className="loading-state">
          Loading BACKTEST quality report...
        </p>
      </main>
    );
  }

  if (state.status === "error") {
    return (
      <main className="quality-page">
        <Header
          workspaceId={workspaceId}
          runId={runId}
          selectedHorizon={selectedHorizon}
          onHorizonChange={handleHorizonChange}
        />
        <div role="alert" className="error-state">
          {state.message}
        </div>
      </main>
    );
  }

  return (
    <main className="quality-page">
      <Header
        workspaceId={workspaceId}
        runId={runId}
        report={state.report}
        selectedHorizon={selectedHorizon}
        onHorizonChange={handleHorizonChange}
      />
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
  selectedHorizon,
  onHorizonChange,
  report,
}: {
  workspaceId: string;
  runId: string;
  selectedHorizon: SupportedQualityHorizon;
  onHorizonChange: (horizon: SupportedQualityHorizon) => void;
  report?: BacktestQualityReport;
}) {
  const reportHorizon = report?.horizon ?? selectedHorizon;
  return (
    <header className="quality-header">
      <div>
        <p className="eyebrow">BTCUSD BACKTEST</p>
        <h1>Backtest quality report</h1>
        <p className="safety-copy">
          BACKTEST-only analytical dataset quality indicator for historical
          BTCUSD evaluation. This view evaluates directional bias quality only.
        </p>
        <label className="horizon-control">
          Quality horizon
          <select
            value={selectedHorizon.key}
            onChange={(event) =>
              onHorizonChange(horizonFromKey(event.currentTarget.value))
            }
          >
            {SUPPORTED_QUALITY_HORIZONS.map((horizon) => (
              <option key={horizon.key} value={horizon.key}>
                {horizon.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <dl className="metadata-grid" aria-label="Report metadata">
        <MetadataItem label="Workspace" value={report?.workspace_id ?? workspaceId} />
        <MetadataItem label="Run" value={report?.run_id ?? runId} />
        <MetadataItem label="Instrument" value={report?.instrument ?? "BTCUSD"} />
        <MetadataItem label="Mode" value={report?.mode ?? "BACKTEST"} />
        <MetadataItem label="Horizon" value={formatHorizon(reportHorizon)} />
        {report ? (
          <>
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
  const [filterText, setFilterText] = useState("");
  const [biasFilter, setBiasFilter] = useState<DirectionalBias | "ALL">("ALL");
  const [relevanceFilter, setRelevanceFilter] = useState<RelevanceLabel | "ALL">(
    "ALL",
  );
  const visibleRecords = records.filter((record) =>
    recordMatchesFilters(record, {
      bias: biasFilter,
      relevance: relevanceFilter,
      text: filterText,
    }),
  );

  return (
    <section className="records-panel" aria-labelledby="records-heading">
      <div className="section-heading">
        <h2 id="records-heading">Representative records</h2>
        <span>
          {visibleRecords.length}/{records.length}
        </span>
      </div>
      {records.length > 0 ? (
        <div className="filter-bar" aria-label="Representative records filters">
          <label>
            Filter records
            <input
              value={filterText}
              onChange={(event) => setFilterText(event.currentTarget.value)}
              placeholder="Headline, source, timestamp"
            />
          </label>
          <label>
            Directional bias
            <select
              value={biasFilter}
              onChange={(event) =>
                setBiasFilter(event.currentTarget.value as DirectionalBias | "ALL")
              }
            >
              <option value="ALL">All</option>
              <option value="LONG">LONG</option>
              <option value="SHORT">SHORT</option>
              <option value="FLAT">FLAT</option>
            </select>
          </label>
          <label>
            Relevance
            <select
              value={relevanceFilter}
              onChange={(event) =>
                setRelevanceFilter(event.currentTarget.value as RelevanceLabel | "ALL")
              }
            >
              <option value="ALL">All</option>
              <option value="RELEVANT">RELEVANT</option>
              <option value="NOISE">NOISE</option>
              <option value="IRRELEVANT">IRRELEVANT</option>
            </select>
          </label>
        </div>
      ) : null}
      {records.length === 0 ? (
        <p role="status" className="empty-state">
          No representative records are available for this BACKTEST report.
        </p>
      ) : visibleRecords.length === 0 ? (
        <p role="status" className="empty-state">
          No representative records match the selected filters.
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
              {visibleRecords.map((record) => (
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

function recordMatchesFilters(
  record: QualityInputRecord,
  filters: {
    bias: DirectionalBias | "ALL";
    relevance: RelevanceLabel | "ALL";
    text: string;
  },
): boolean {
  if (filters.bias !== "ALL" && record.directional_bias !== filters.bias) {
    return false;
  }
  if (filters.relevance !== "ALL" && record.relevance !== filters.relevance) {
    return false;
  }

  const query = filters.text.trim().toLowerCase();
  if (!query) {
    return true;
  }

  return [
    record.event_timestamp,
    record.headline,
    record.source_id,
    record.source_name,
    record.sentiment_score.toFixed(2),
    record.directional_bias,
    record.later_return === null ? "missing" : formatReturn(record.later_return),
    record.realized_direction ?? "missing",
    record.relevance,
  ].some((value) => value?.toLowerCase().includes(query));
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

function horizonFromSearch(search: string): SupportedQualityHorizon {
  const params = new URLSearchParams(search);
  const value = Number(params.get("horizon_value"));
  const unit = params.get("horizon_unit");

  if (!Number.isInteger(value) || !isHorizonUnit(unit)) {
    return DEFAULT_QUALITY_HORIZON;
  }

  return findSupportedHorizon(value, unit) ?? DEFAULT_QUALITY_HORIZON;
}

function horizonFromKey(key: string): SupportedQualityHorizon {
  return (
    SUPPORTED_QUALITY_HORIZONS.find((horizon) => horizon.key === key) ??
    DEFAULT_QUALITY_HORIZON
  );
}

function findSupportedHorizon(
  value: number,
  unit: HorizonUnit,
): SupportedQualityHorizon | null {
  return (
    SUPPORTED_QUALITY_HORIZONS.find(
      (horizon) => horizon.value === value && horizon.unit === unit,
    ) ?? null
  );
}

function isHorizonUnit(value: string | null): value is HorizonUnit {
  return value === "minutes" || value === "hours" || value === "days";
}

function updateUrlHorizon(horizon: SupportedQualityHorizon): void {
  const url = new URL(window.location.href);
  url.searchParams.set("horizon_value", String(horizon.value));
  url.searchParams.set("horizon_unit", horizon.unit);
  window.history.pushState({}, "", `${url.pathname}${url.search}${url.hash}`);
}

function formatHorizon(horizon: QualityHorizon): string {
  return findSupportedHorizon(horizon.value, horizon.unit)?.label ?? (
    `${horizon.value} ${horizon.unit}`
  );
}
