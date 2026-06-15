import { FormEvent, useMemo, useState } from "react";

import {
  createBacktestRunShell,
  downloadBacktestDatasetExport,
  runBacktestDataset,
  type BacktestShellApiError,
} from "./api";
import type {
  BacktestRunShell,
  CreateBacktestRunRequest,
  DatasetPreviewRecord,
  DatasetRunPreview,
} from "./types";

const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;

type CreateRun = (
  workspaceId: string,
  request: CreateBacktestRunRequest,
) => Promise<BacktestRunShell>;

type RunDataset = (workspaceId: string, runId: string) => Promise<DatasetRunPreview>;
type DownloadDatasetExport = (workspaceId: string, runId: string) => Promise<void>;

interface BacktestShellPageProps {
  workspaceId: string;
  createRun?: CreateRun;
  runDataset?: RunDataset;
  downloadDatasetExport?: DownloadDatasetExport;
  now?: Date;
}

type SubmitState =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "created"; run: BacktestRunShell }
  | { status: "error"; message: string };

type DatasetState =
  | { status: "idle" }
  | { status: "running" }
  | { status: "completed"; preview: DatasetRunPreview }
  | { status: "provider-limited"; preview: DatasetRunPreview; message: string }
  | { status: "error"; message: string };

type ExportState =
  | { status: "idle" }
  | { status: "downloading" }
  | { status: "error"; message: string };

export function BacktestShellPage({
  workspaceId,
  createRun = createBacktestRunShell,
  runDataset = runBacktestDataset,
  downloadDatasetExport = downloadBacktestDatasetExport,
  now = new Date(),
}: BacktestShellPageProps) {
  const defaults = useMemo(() => defaultTimeframe(now), [now]);
  const [timeframeStart, setTimeframeStart] = useState(defaults.timeframeStart);
  const [timeframeEnd, setTimeframeEnd] = useState(defaults.timeframeEnd);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const [submitState, setSubmitState] = useState<SubmitState>({ status: "idle" });
  const [datasetState, setDatasetState] = useState<DatasetState>({ status: "idle" });
  const [exportState, setExportState] = useState<ExportState>({ status: "idle" });

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validation = validateTimeframe(timeframeStart, timeframeEnd);
    setValidationMessage(validation);

    if (validation) {
      return;
    }

    setSubmitState({ status: "submitting" });
    try {
      const run = await createRun(workspaceId, {
        instrument: "BTCUSD",
        mode: "BACKTEST",
        timeframe_start: timeframeStart,
        timeframe_end: timeframeEnd,
      });
      setSubmitState({ status: "created", run });
      setDatasetState({ status: "idle" });
      setExportState({ status: "idle" });
    } catch (error) {
      setSubmitState({
        status: "error",
        message: errorMessage(error),
      });
    }
  }

  async function handleRunDataset(run: BacktestRunShell) {
    setDatasetState({ status: "running" });
    setExportState({ status: "idle" });
    try {
      const preview = await runDataset(workspaceId, run.run_id);
      setDatasetState({ status: "completed", preview });
    } catch (error) {
      const apiError = error as Partial<BacktestShellApiError>;
      if (isDatasetRunPreview(apiError.payload)) {
        setDatasetState({
          status: "provider-limited",
          preview: apiError.payload,
          message: errorMessage(error),
        });
        return;
      }
      setDatasetState({
        status: "error",
        message: errorMessage(error),
      });
    }
  }

  async function handleDownloadDatasetExport(run: BacktestRunShell) {
    setExportState({ status: "downloading" });
    try {
      await downloadDatasetExport(workspaceId, run.run_id);
      setExportState({ status: "idle" });
    } catch (error) {
      setExportState({
        status: "error",
        message: errorMessage(error),
      });
    }
  }

  return (
    <main className="quality-page shell-page">
      <header className="quality-header">
        <div>
          <p className="eyebrow">BTCUSD BACKTEST</p>
          <h1>Workspace backtest shell</h1>
          <p className="safety-copy">
            Draft workspace run setup for historical BTCUSD directional bias
            datasets. The shell records workspace, instrument, mode, and
            timeframe only.
          </p>
        </div>
        <dl className="metadata-grid" aria-label="Shell metadata">
          <MetadataItem label="Workspace" value={workspaceId} />
          <MetadataItem label="Instrument" value="BTCUSD" />
          <MetadataItem label="Mode" value="BACKTEST" />
          <MetadataItem label="Storage" value="Local draft" />
        </dl>
      </header>

      <section className="shell-layout" aria-label="Draft BACKTEST run setup">
        <form className="shell-form" onSubmit={handleSubmit}>
          <div className="form-grid">
            <label>
              Workspace
              <input value={workspaceId} readOnly />
            </label>
            <label>
              Instrument
              <input value="BTCUSD" readOnly />
            </label>
            <label>
              Mode
              <input value="BACKTEST" readOnly />
            </label>
            <label>
              Status
              <input value="DRAFT" readOnly />
            </label>
            <label>
              Timeframe start
              <input
                value={timeframeStart}
                onChange={(event) => setTimeframeStart(event.target.value)}
                aria-describedby="timeframe-help"
              />
            </label>
            <label>
              Timeframe end
              <input
                value={timeframeEnd}
                onChange={(event) => setTimeframeEnd(event.target.value)}
                aria-describedby="timeframe-help"
              />
            </label>
          </div>
          <p id="timeframe-help" className="field-help">
            Use timezone-aware ISO timestamps. BACKTEST range is limited to 30
            days.
          </p>
          {validationMessage ? (
            <div className="inline-alert" role="alert">
              {validationMessage}
            </div>
          ) : null}
          <div className="form-actions">
            <button type="submit" disabled={submitState.status === "submitting"}>
              {submitState.status === "submitting" ? "Creating..." : "Create draft run"}
            </button>
          </div>
        </form>

        <aside className="shell-result" aria-label="Draft run result">
          {submitState.status === "idle" ? (
            <p className="empty-state">
              No draft run has been created in this browser session.
            </p>
          ) : null}
          {submitState.status === "submitting" ? (
            <p role="status" className="loading-state">
              Creating draft BACKTEST run...
            </p>
          ) : null}
          {submitState.status === "error" ? (
            <div role="alert" className="error-state">
              {submitState.message}
            </div>
          ) : null}
          {submitState.status === "created" ? (
            <CreatedRunSummary
              run={submitState.run}
              datasetState={datasetState}
              exportState={exportState}
              onRunDataset={() => void handleRunDataset(submitState.run)}
              onDownloadDatasetExport={() =>
                void handleDownloadDatasetExport(submitState.run)
              }
            />
          ) : null}
        </aside>
      </section>
    </main>
  );
}

function CreatedRunSummary({
  run,
  datasetState,
  exportState,
  onRunDataset,
  onDownloadDatasetExport,
}: {
  run: BacktestRunShell;
  datasetState: DatasetState;
  exportState: ExportState;
  onRunDataset: () => void;
  onDownloadDatasetExport: () => void;
}) {
  return (
    <div className="created-run">
      <div className="section-heading">
        <h2>Draft run created</h2>
        <span>{run.status}</span>
      </div>
      <dl className="metadata-grid" aria-label="Created run metadata">
        <MetadataItem label="Workspace" value={run.workspace_id} />
        <MetadataItem label="Run" value={run.run_id} />
        <MetadataItem label="Instrument" value={run.instrument} />
        <MetadataItem label="Mode" value={run.mode} />
        <MetadataItem label="Start" value={run.timeframe_start} />
        <MetadataItem label="End" value={run.timeframe_end} />
        <MetadataItem label="Created" value={run.created_at} />
        <MetadataItem label="Status" value={run.status} />
      </dl>
      <div className="dataset-actions">
        <button type="button" onClick={onRunDataset} disabled={datasetState.status === "running"}>
          {datasetState.status === "running"
            ? "Running deterministic dataset..."
            : "Run deterministic BACKTEST dataset"}
        </button>
      </div>
      {run.quality_report_path && datasetState.status !== "completed" ? (
        <p className="quality-link-note">
          <a href={run.quality_report_path}>Quality route</a> is unavailable
          until S-02 produces a completed deterministic dataset.
        </p>
      ) : null}
      <DatasetPanel
        run={run}
        datasetState={datasetState}
        exportState={exportState}
        onDownloadDatasetExport={onDownloadDatasetExport}
      />
    </div>
  );
}

function DatasetPanel({
  run,
  datasetState,
  exportState,
  onDownloadDatasetExport,
}: {
  run: BacktestRunShell;
  datasetState: DatasetState;
  exportState: ExportState;
  onDownloadDatasetExport: () => void;
}) {
  if (datasetState.status === "idle") {
    return (
      <p className="dataset-note">
        Deterministic dataset generation starts only after the explicit BACKTEST
        action above.
      </p>
    );
  }
  if (datasetState.status === "running") {
    return (
      <p role="status" className="loading-state">
        Running deterministic BACKTEST dataset...
      </p>
    );
  }
  if (datasetState.status === "error") {
    return (
      <div role="alert" className="error-state">
        {datasetState.message}
      </div>
    );
  }

  const preview = datasetState.preview;
  const isProviderLimited = datasetState.status === "provider-limited";
  return (
    <section
      className={isProviderLimited ? "dataset-panel provider-limited" : "dataset-panel"}
      aria-label="Dataset run result"
    >
      <div className="section-heading">
        <h2>
          {isProviderLimited
            ? "Provider limitation"
            : "Completed deterministic dataset"}
        </h2>
        <span>{preview.summary.status}</span>
      </div>
      {isProviderLimited ? (
        <div role="alert" className="inline-alert">
          {datasetState.message}
        </div>
      ) : null}
      <dl className="metadata-grid" aria-label="Dataset summary metadata">
        <MetadataItem label="Provider" value={preview.summary.provider_name} />
        <MetadataItem label="Records" value={String(preview.summary.record_count)} />
        <MetadataItem label="Relevant" value={String(preview.summary.relevant_count)} />
        <MetadataItem label="Noise" value={String(preview.summary.noise_count)} />
        <MetadataItem
          label="Irrelevant"
          value={String(preview.summary.irrelevant_count)}
        />
        <MetadataItem label="Model" value={preview.summary.model_version} />
        <MetadataItem label="Config" value={preview.summary.config_version} />
        <MetadataItem
          label="Fingerprint"
          value={preview.summary.input_fingerprint}
        />
      </dl>
      {isProviderLimited ? (
        <ProviderLimitationDetails preview={preview} />
      ) : (
        <>
          <p className="quality-link-note">
            <a href={run.quality_report_path ?? "#"}>Quality route</a> is
            available for this completed dataset. Movement fields remain pending
            price enrichment.
          </p>
          <div className="dataset-actions export-actions">
            <button
              type="button"
              onClick={onDownloadDatasetExport}
              disabled={exportState.status === "downloading"}
            >
              {exportState.status === "downloading"
                ? "Preparing JSONL download..."
                : "Download JSONL dataset"}
            </button>
          </div>
          {exportState.status === "error" ? (
            <div role="alert" className="inline-alert">
              {exportState.message}
            </div>
          ) : null}
          <DatasetPreviewTable records={preview.records} />
        </>
      )}
    </section>
  );
}

function ProviderLimitationDetails({ preview }: { preview: DatasetRunPreview }) {
  const limitation = preview.summary.provider_limitation;
  if (!limitation) {
    return null;
  }
  return (
    <dl className="metadata-grid provider-limitation-metadata" aria-label="Provider limitation metadata">
      <MetadataItem label="Provider" value={limitation.provider_name} />
      <MetadataItem label="Reason" value={limitation.reason} />
      {limitation.detail ? <MetadataItem label="Detail" value={limitation.detail} /> : null}
    </dl>
  );
}

function DatasetPreviewTable({ records }: { records: DatasetPreviewRecord[] }) {
  if (records.length === 0) {
    return <p className="empty-state">No preview records returned.</p>;
  }

  return (
    <div className="records-panel dataset-preview-panel">
      <div className="section-heading">
        <h2>Preview records</h2>
        <span>{records.length}</span>
      </div>
      <div className="table-wrap">
        <table aria-label="Dataset preview records">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Headline</th>
              <th>Bias</th>
              <th>Confidence</th>
              <th>Relevance</th>
            </tr>
          </thead>
          <tbody>
            {records.map((record) => (
              <tr key={record.record_id ?? `${record.timestamp}-${record.headline}`}>
                <td>{record.timestamp}</td>
                <td>{record.headline}</td>
                <td>{record.directional_bias}</td>
                <td>{record.confidence.toFixed(4)}</td>
                <td>{record.relevance}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
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

function defaultTimeframe(now: Date) {
  return {
    timeframeStart: new Date(now.getTime() - THIRTY_DAYS_MS).toISOString(),
    timeframeEnd: now.toISOString(),
  };
}

function validateTimeframe(timeframeStart: string, timeframeEnd: string): string | null {
  const start = parseIsoTimestamp(timeframeStart);
  const end = parseIsoTimestamp(timeframeEnd);

  if (!start || !end) {
    return "Timeframe values must be timezone-aware ISO timestamps.";
  }
  if (end.getTime() < start.getTime()) {
    return "Timeframe end must be greater than or equal to timeframe start.";
  }
  if (end.getTime() - start.getTime() > THIRTY_DAYS_MS) {
    return "BACKTEST timeframe range must be no more than 30 days.";
  }

  return null;
}

function parseIsoTimestamp(value: string): Date | null {
  if (!/(Z|[+-]\d{2}:\d{2})$/.test(value)) {
    return null;
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }

  return parsed;
}

function errorMessage(error: unknown): string {
  const apiError = error as Partial<BacktestShellApiError>;
  if (typeof apiError.detail === "string" && apiError.detail.length > 0) {
    return apiError.detail;
  }
  if (error instanceof Error) {
    return error.message;
  }

  return "Draft BACKTEST run could not be created.";
}

function isDatasetRunPreview(value: unknown): value is DatasetRunPreview {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<DatasetRunPreview>;
  return Boolean(candidate.summary && Array.isArray(candidate.records));
}
