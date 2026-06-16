import { useEffect, useState } from "react";

import {
  downloadBacktestDatasetExport,
  runBacktestDataset,
  type BacktestShellApiError,
} from "../backtestShell/api";
import type { DatasetRunPreview } from "../backtestShell/types";
import { fetchBacktestRunHistory } from "./api";
import type {
  BacktestRunHistoryItem,
  BacktestRunHistoryResponse,
} from "./types";

type LoadRunHistory = (workspaceId: string) => Promise<BacktestRunHistoryResponse>;
type RunDataset = (workspaceId: string, runId: string) => Promise<DatasetRunPreview>;
type DownloadDatasetExport = (workspaceId: string, runId: string) => Promise<void>;

interface BacktestRunHistoryPageProps {
  workspaceId: string;
  loadRunHistory?: LoadRunHistory;
  runDataset?: RunDataset;
  downloadDatasetExport?: DownloadDatasetExport;
}

type LoadState =
  | { status: "loading" }
  | { status: "loaded"; history: BacktestRunHistoryResponse }
  | { status: "error"; message: string };

type RunState =
  | { status: "idle" }
  | { status: "running"; runId: string }
  | { status: "error"; runId: string; message: string };

type ExportState =
  | { status: "idle" }
  | { status: "downloading"; runId: string }
  | { status: "error"; runId: string; message: string };

export function BacktestRunHistoryPage({
  workspaceId,
  loadRunHistory = fetchBacktestRunHistory,
  runDataset = runBacktestDataset,
  downloadDatasetExport = downloadBacktestDatasetExport,
}: BacktestRunHistoryPageProps) {
  const [loadState, setLoadState] = useState<LoadState>({ status: "loading" });
  const [runState, setRunState] = useState<RunState>({ status: "idle" });
  const [exportState, setExportState] = useState<ExportState>({ status: "idle" });

  useEffect(() => {
    let isCurrent = true;
    setLoadState({ status: "loading" });

    loadRunHistory(workspaceId)
      .then((history) => {
        if (isCurrent) {
          setLoadState({ status: "loaded", history });
        }
      })
      .catch((error: Error) => {
        if (isCurrent) {
          setLoadState({ status: "error", message: errorMessage(error) });
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [loadRunHistory, workspaceId]);

  async function refreshHistory() {
    const history = await loadRunHistory(workspaceId);
    setLoadState({ status: "loaded", history });
  }

  async function handleRunDataset(run: BacktestRunHistoryItem) {
    setRunState({ status: "running", runId: run.run_id });
    setExportState({ status: "idle" });
    try {
      await runDataset(workspaceId, run.run_id);
      await refreshHistory();
      setRunState({ status: "idle" });
    } catch (error) {
      const apiError = error as Partial<BacktestShellApiError>;
      if (isDatasetRunPreview(apiError.payload)) {
        await refreshHistory();
        setRunState({ status: "idle" });
        return;
      }
      setRunState({
        status: "error",
        runId: run.run_id,
        message: errorMessage(error),
      });
    }
  }

  async function handleDownloadDatasetExport(run: BacktestRunHistoryItem) {
    setExportState({ status: "downloading", runId: run.run_id });
    try {
      await downloadDatasetExport(workspaceId, run.run_id);
      setExportState({ status: "idle" });
    } catch (error) {
      setExportState({
        status: "error",
        runId: run.run_id,
        message: errorMessage(error),
      });
    }
  }

  return (
    <main className="quality-page run-history-page">
      <header className="quality-header">
        <div>
          <p className="eyebrow">BTCUSD BACKTEST</p>
          <h1>BACKTEST run history</h1>
          <p className="safety-copy">
            Recover workspace draft and completed deterministic directional bias
            datasets after sign-out or browser refresh.
          </p>
        </div>
        <dl className="metadata-grid" aria-label="Run history metadata">
          <MetadataItem label="Workspace" value={workspaceId} />
          <MetadataItem label="Instrument" value="BTCUSD" />
          <MetadataItem label="Mode" value="BACKTEST" />
          <MetadataItem label="Storage" value="Postgres workspace" />
        </dl>
      </header>

      <section className="shell-result run-history-panel" aria-labelledby="run-history-heading">
        <div className="section-heading">
          <h2 id="run-history-heading">Workspace runs</h2>
          {loadState.status === "loaded" ? (
            <span>{loadState.history.runs.length}</span>
          ) : null}
        </div>

        {loadState.status === "loading" ? (
          <p role="status" className="loading-state">
            Loading BACKTEST run history...
          </p>
        ) : null}
        {loadState.status === "error" ? (
          <div role="alert" className="error-state">
            {loadState.message}
          </div>
        ) : null}
        {loadState.status === "loaded" && loadState.history.runs.length === 0 ? (
          <p className="empty-state">
            No BACKTEST runs exist for this workspace yet.
          </p>
        ) : null}
        {loadState.status === "loaded" && loadState.history.runs.length > 0 ? (
          <div className="run-history-list">
            {loadState.history.runs.map((run) => (
              <RunHistoryCard
                key={run.run_id}
                run={run}
                runState={runState}
                exportState={exportState}
                onRunDataset={() => void handleRunDataset(run)}
                onDownloadDatasetExport={() =>
                  void handleDownloadDatasetExport(run)
                }
              />
            ))}
          </div>
        ) : null}
      </section>
    </main>
  );
}

function RunHistoryCard({
  run,
  runState,
  exportState,
  onRunDataset,
  onDownloadDatasetExport,
}: {
  run: BacktestRunHistoryItem;
  runState: RunState;
  exportState: ExportState;
  onRunDataset: () => void;
  onDownloadDatasetExport: () => void;
}) {
  const isRunningThisRun =
    runState.status === "running" && runState.runId === run.run_id;
  const isDownloadingThisRun =
    exportState.status === "downloading" && exportState.runId === run.run_id;
  const isCompleted = run.dataset_status === "COMPLETED";
  const isProviderLimited = run.dataset_status === "FAILED_PROVIDER_LIMITATION";
  const canRunDataset =
    run.dataset_status === null || run.dataset_status === "DRAFT";

  return (
    <article className="run-history-card">
      <div className="section-heading run-history-card-header">
        <div>
          <h3>{run.config_name ?? run.run_id}</h3>
          <p>{run.config_name ? run.run_id : "No saved configuration"}</p>
        </div>
        <span className="status-pill">{run.dataset_status ?? run.status}</span>
      </div>

      <dl className="metadata-grid" aria-label={`${run.run_id} metadata`}>
        <MetadataItem label="Run" value={run.run_id} />
        <MetadataItem label="Saved config" value={run.config_name ?? "None"} />
        <MetadataItem label="Start" value={run.timeframe_start} />
        <MetadataItem label="End" value={run.timeframe_end} />
        <MetadataItem label="Created" value={run.created_at} />
        <MetadataItem label="Provider" value={run.provider_name ?? "Pending"} />
        <MetadataItem label="Records" value={countValue(run.record_count)} />
        <MetadataItem label="Relevant" value={countValue(run.relevant_count)} />
        <MetadataItem label="Noise" value={countValue(run.noise_count)} />
        <MetadataItem label="Irrelevant" value={countValue(run.irrelevant_count)} />
        <MetadataItem label="Model" value={run.model_version ?? "Pending"} />
        <MetadataItem label="Policy" value={run.config_version ?? "Pending"} />
        <MetadataItem
          label="Fingerprint"
          value={run.input_fingerprint ?? "Pending"}
        />
      </dl>

      {runState.status === "error" && runState.runId === run.run_id ? (
        <div role="alert" className="inline-alert">
          {runState.message}
        </div>
      ) : null}

      {exportState.status === "error" && exportState.runId === run.run_id ? (
        <div role="alert" className="inline-alert">
          {exportState.message}
        </div>
      ) : null}

      {isProviderLimited ? <ProviderLimitationDetails run={run} /> : null}

      <RunHistorySummary
        run={run}
        isCompleted={isCompleted}
        isProviderLimited={isProviderLimited}
      />

      <div className="run-history-actions">
        {canRunDataset ? (
          <button type="button" onClick={onRunDataset} disabled={isRunningThisRun}>
            {isRunningThisRun
              ? "Running deterministic dataset..."
              : "Run deterministic BACKTEST dataset"}
          </button>
        ) : null}
        {run.dataset_status === "RUNNING" ? (
          <button type="button" disabled>
            Dataset run in progress
          </button>
        ) : null}
        {isCompleted && run.quality_report_path ? (
          <a href={run.quality_report_path}>Open quality report</a>
        ) : null}
        {isCompleted && run.dataset_export_path ? (
          <button
            type="button"
            onClick={onDownloadDatasetExport}
            disabled={isDownloadingThisRun}
          >
            {isDownloadingThisRun
              ? "Preparing JSONL download..."
              : "Download JSONL dataset"}
          </button>
        ) : null}
      </div>
    </article>
  );
}

function RunHistorySummary({
  run,
  isCompleted,
  isProviderLimited,
}: {
  run: BacktestRunHistoryItem;
  isCompleted: boolean;
  isProviderLimited: boolean;
}) {
  if (isCompleted) {
    return (
      <p className="dataset-note">
        Completed deterministic dataset. Quality can be opened from this
        historical run; movement fields remain pending price enrichment.
      </p>
    );
  }

  if (isProviderLimited) {
    return (
      <p className="dataset-note">
        Provider limitation is preserved as historical workspace work and does
        not expose quality or JSONL as completed output.
      </p>
    );
  }

  if (run.dataset_status === "RUNNING") {
    return (
      <p className="dataset-note">
        Dataset generation has started for this BACKTEST run.
      </p>
    );
  }

  return (
    <p className="dataset-note">
      No terminal deterministic dataset exists for this BACKTEST run yet.
    </p>
  );
}

function ProviderLimitationDetails({ run }: { run: BacktestRunHistoryItem }) {
  const limitation = run.provider_limitation;
  if (!limitation) {
    return null;
  }

  return (
    <dl
      className="metadata-grid provider-limitation-metadata"
      aria-label={`${run.run_id} provider limitation metadata`}
    >
      <MetadataItem label="Provider" value={limitation.provider_name} />
      <MetadataItem label="Reason" value={limitation.reason} />
      {limitation.detail ? (
        <MetadataItem label="Detail" value={limitation.detail} />
      ) : null}
    </dl>
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

function countValue(value: number | null): string {
  return value === null ? "Pending" : String(value);
}

function errorMessage(error: unknown): string {
  const apiError = error as Partial<BacktestShellApiError>;
  if (typeof apiError.detail === "string" && apiError.detail.length > 0) {
    return apiError.detail;
  }
  if (error instanceof Error) {
    return error.message;
  }

  return "BACKTEST run history request failed.";
}

function isDatasetRunPreview(value: unknown): value is DatasetRunPreview {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<DatasetRunPreview>;
  return Boolean(candidate.summary && Array.isArray(candidate.records));
}
