import { FormEvent, useMemo, useState } from "react";

import {
  createBacktestRunShell,
  type BacktestShellApiError,
} from "./api";
import type { BacktestRunShell, CreateBacktestRunRequest } from "./types";

const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;

type CreateRun = (
  workspaceId: string,
  request: CreateBacktestRunRequest,
) => Promise<BacktestRunShell>;

interface BacktestShellPageProps {
  workspaceId: string;
  createRun?: CreateRun;
  now?: Date;
}

type SubmitState =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "created"; run: BacktestRunShell }
  | { status: "error"; message: string };

export function BacktestShellPage({
  workspaceId,
  createRun = createBacktestRunShell,
  now = new Date(),
}: BacktestShellPageProps) {
  const defaults = useMemo(() => defaultTimeframe(now), [now]);
  const [timeframeStart, setTimeframeStart] = useState(defaults.timeframeStart);
  const [timeframeEnd, setTimeframeEnd] = useState(defaults.timeframeEnd);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const [submitState, setSubmitState] = useState<SubmitState>({ status: "idle" });

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
    } catch (error) {
      setSubmitState({
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
            <CreatedRunSummary run={submitState.run} />
          ) : null}
        </aside>
      </section>
    </main>
  );
}

function CreatedRunSummary({ run }: { run: BacktestRunShell }) {
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
      {run.quality_report_path ? (
        <p className="quality-link-note">
          <a href={run.quality_report_path}>Quality route</a> is unavailable
          until S-02 produces a completed deterministic dataset.
        </p>
      ) : null}
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
