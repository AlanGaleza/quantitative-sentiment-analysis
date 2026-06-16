import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  downloadBacktestDatasetExport,
  runBacktestDataset,
  type BacktestShellApiError,
} from "../backtestShell/api";
import type {
  BacktestRunShell,
  DatasetRunPreview,
} from "../backtestShell/types";
import {
  createBacktestConfig,
  createDraftFromBacktestConfig,
  deleteBacktestConfig,
  listBacktestConfigs,
  updateBacktestConfig,
  type BacktestConfig,
  type CreateBacktestConfigRequest,
  type UpdateBacktestConfigRequest,
} from "./api";

const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;

type LoadConfigs = (workspaceId: string) => Promise<BacktestConfig[]>;
type CreateConfig = (
  workspaceId: string,
  request: CreateBacktestConfigRequest,
) => Promise<BacktestConfig>;
type UpdateConfig = (
  workspaceId: string,
  configId: string,
  request: UpdateBacktestConfigRequest,
) => Promise<BacktestConfig>;
type DeleteConfig = (workspaceId: string, configId: string) => Promise<void>;
type CreateDraft = (
  workspaceId: string,
  configId: string,
) => Promise<BacktestRunShell>;
type RunDataset = (workspaceId: string, runId: string) => Promise<DatasetRunPreview>;
type DownloadDatasetExport = (workspaceId: string, runId: string) => Promise<void>;

interface BacktestConfigPageProps {
  workspaceId: string;
  loadConfigs?: LoadConfigs;
  createConfig?: CreateConfig;
  updateConfig?: UpdateConfig;
  removeConfig?: DeleteConfig;
  createDraft?: CreateDraft;
  runDataset?: RunDataset;
  downloadDatasetExport?: DownloadDatasetExport;
  now?: Date;
}

type LoadState =
  | { status: "loading" }
  | { status: "loaded"; configs: BacktestConfig[] }
  | { status: "error"; message: string };

type SaveState =
  | { status: "idle" }
  | { status: "saving" }
  | { status: "error"; message: string };

type DeleteState =
  | { status: "idle" }
  | { status: "confirm"; configId: string }
  | { status: "deleting"; configId: string }
  | { status: "error"; message: string };

type DraftState =
  | { status: "idle" }
  | { status: "creating"; configId: string }
  | { status: "created"; run: BacktestRunShell; configName: string }
  | { status: "running"; run: BacktestRunShell; configName: string }
  | {
      status: "completed";
      run: BacktestRunShell;
      configName: string;
      preview: DatasetRunPreview;
    }
  | {
      status: "provider-limited";
      run: BacktestRunShell;
      configName: string;
      preview: DatasetRunPreview;
      message: string;
    }
  | { status: "error"; message: string };

type ExportState =
  | { status: "idle" }
  | { status: "downloading" }
  | { status: "error"; message: string };

interface ConfigFormState {
  name: string;
  timeframeStart: string;
  timeframeEnd: string;
  editingConfigId: string | null;
}

export function BacktestConfigPage({
  workspaceId,
  loadConfigs = listBacktestConfigs,
  createConfig = createBacktestConfig,
  updateConfig = updateBacktestConfig,
  removeConfig = deleteBacktestConfig,
  createDraft = createDraftFromBacktestConfig,
  runDataset: runDatasetForDraft = runBacktestDataset,
  downloadDatasetExport: downloadDataset = downloadBacktestDatasetExport,
  now = new Date(),
}: BacktestConfigPageProps) {
  const defaults = useMemo(() => defaultTimeframe(now), [now]);
  const [loadState, setLoadState] = useState<LoadState>({ status: "loading" });
  const [formState, setFormState] = useState<ConfigFormState>({
    name: "",
    timeframeStart: defaults.timeframeStart,
    timeframeEnd: defaults.timeframeEnd,
    editingConfigId: null,
  });
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<SaveState>({ status: "idle" });
  const [deleteState, setDeleteState] = useState<DeleteState>({ status: "idle" });
  const [draftState, setDraftState] = useState<DraftState>({ status: "idle" });
  const [exportState, setExportState] = useState<ExportState>({ status: "idle" });

  useEffect(() => {
    let isCurrent = true;
    setLoadState({ status: "loading" });

    loadConfigs(workspaceId)
      .then((configs) => {
        if (isCurrent) {
          setLoadState({ status: "loaded", configs });
        }
      })
      .catch((error: Error) => {
        if (isCurrent) {
          setLoadState({ status: "error", message: error.message });
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [loadConfigs, workspaceId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validation = validateForm(formState);
    setValidationMessage(validation);

    if (validation) {
      return;
    }

    setSaveState({ status: "saving" });
    const request = configRequest(formState);

    try {
      if (formState.editingConfigId) {
        const updated = await updateConfig(
          workspaceId,
          formState.editingConfigId,
          request,
        );
        replaceConfig(updated);
      } else {
        const created = await createConfig(workspaceId, request);
        appendConfig(created);
      }
      setFormState({
        name: "",
        timeframeStart: defaults.timeframeStart,
        timeframeEnd: defaults.timeframeEnd,
        editingConfigId: null,
      });
      setSaveState({ status: "idle" });
    } catch (error) {
      setSaveState({ status: "error", message: errorMessage(error) });
    }
  }

  function handleEdit(config: BacktestConfig) {
    setFormState({
      name: config.name,
      timeframeStart: config.timeframe_start,
      timeframeEnd: config.timeframe_end,
      editingConfigId: config.id,
    });
    setValidationMessage(null);
    setSaveState({ status: "idle" });
  }

  function cancelEdit() {
    setFormState({
      name: "",
      timeframeStart: defaults.timeframeStart,
      timeframeEnd: defaults.timeframeEnd,
      editingConfigId: null,
    });
    setValidationMessage(null);
  }

  async function confirmDelete(config: BacktestConfig) {
    setDeleteState({ status: "deleting", configId: config.id });
    try {
      await removeConfig(workspaceId, config.id);
      removeConfigFromList(config.id);
      if (formState.editingConfigId === config.id) {
        cancelEdit();
      }
      setDeleteState({ status: "idle" });
    } catch (error) {
      setDeleteState({ status: "error", message: errorMessage(error) });
    }
  }

  async function handleCreateDraft(config: BacktestConfig) {
    setDraftState({ status: "creating", configId: config.id });
    setExportState({ status: "idle" });
    try {
      const run = await createDraft(workspaceId, config.id);
      setDraftState({ status: "created", run, configName: config.name });
    } catch (error) {
      setDraftState({ status: "error", message: errorMessage(error) });
    }
  }

  async function handleRunDataset(run: BacktestRunShell, configName: string) {
    setDraftState({ status: "running", run, configName });
    setExportState({ status: "idle" });
    try {
      const preview = await runDatasetForDraft(workspaceId, run.run_id);
      setDraftState({ status: "completed", run, configName, preview });
    } catch (error) {
      const apiError = error as Partial<BacktestShellApiError>;
      if (isDatasetRunPreview(apiError.payload)) {
        setDraftState({
          status: "provider-limited",
          run,
          configName,
          preview: apiError.payload,
          message: errorMessage(error),
        });
        return;
      }
      setDraftState({ status: "error", message: errorMessage(error) });
    }
  }

  async function handleDownload(run: BacktestRunShell) {
    setExportState({ status: "downloading" });
    try {
      await downloadDataset(workspaceId, run.run_id);
      setExportState({ status: "idle" });
    } catch (error) {
      setExportState({ status: "error", message: errorMessage(error) });
    }
  }

  function appendConfig(config: BacktestConfig) {
    setLoadState((current) => {
      if (current.status !== "loaded") {
        return { status: "loaded", configs: [config] };
      }
      return { status: "loaded", configs: [config, ...current.configs] };
    });
  }

  function replaceConfig(config: BacktestConfig) {
    setLoadState((current) => {
      if (current.status !== "loaded") {
        return current;
      }
      return {
        status: "loaded",
        configs: current.configs.map((item) =>
          item.id === config.id ? config : item,
        ),
      };
    });
  }

  function removeConfigFromList(configId: string) {
    setLoadState((current) => {
      if (current.status !== "loaded") {
        return current;
      }
      return {
        status: "loaded",
        configs: current.configs.filter((item) => item.id !== configId),
      };
    });
  }

  return (
    <main className="quality-page config-page">
      <header className="quality-header">
        <div>
          <p className="eyebrow">BTCUSD BACKTEST</p>
          <h1>Saved BACKTEST configurations</h1>
          <p className="safety-copy">
            Create and reuse deterministic workspace configuration inputs for
            historical BTCUSD directional bias datasets.
          </p>
        </div>
        <dl className="metadata-grid" aria-label="Configuration metadata">
          <MetadataItem label="Workspace" value={workspaceId} />
          <MetadataItem label="Instrument" value="BTCUSD" />
          <MetadataItem label="Mode" value="BACKTEST" />
          <MetadataItem label="Storage" value="Postgres workspace" />
        </dl>
      </header>

      <section className="config-layout" aria-label="Configuration workflow">
        <form className="shell-form config-form" onSubmit={handleSubmit} noValidate>
          <div className="section-heading">
            <h2>
              {formState.editingConfigId
                ? "Edit saved configuration"
                : "Create saved configuration"}
            </h2>
            {formState.editingConfigId ? (
              <button className="secondary-button" type="button" onClick={cancelEdit}>
                Cancel edit
              </button>
            ) : null}
          </div>
          <div className="form-grid">
            <label>
              Configuration name
              <input
                value={formState.name}
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    name: event.target.value,
                  }))
                }
                required
              />
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
              Timeframe start
              <input
                value={formState.timeframeStart}
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    timeframeStart: event.target.value,
                  }))
                }
                aria-describedby="config-timeframe-help"
              />
            </label>
            <label>
              Timeframe end
              <input
                value={formState.timeframeEnd}
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    timeframeEnd: event.target.value,
                  }))
                }
                aria-describedby="config-timeframe-help"
              />
            </label>
          </div>
          <p id="config-timeframe-help" className="field-help">
            Use timezone-aware ISO timestamps. Saved BACKTEST configuration
            ranges are limited to 30 days.
          </p>
          {validationMessage ? (
            <div className="inline-alert" role="alert">
              {validationMessage}
            </div>
          ) : null}
          {saveState.status === "error" ? (
            <div className="inline-alert" role="alert">
              {saveState.message}
            </div>
          ) : null}
          <div className="form-actions">
            <button type="submit" disabled={saveState.status === "saving"}>
              {saveState.status === "saving"
                ? "Saving..."
                : formState.editingConfigId
                  ? "Save configuration"
                  : "Create configuration"}
            </button>
          </div>
        </form>

        <section className="shell-result config-list-panel" aria-labelledby="configs-heading">
          <div className="section-heading">
            <h2 id="configs-heading">Workspace configurations</h2>
            {loadState.status === "loaded" ? (
              <span>{loadState.configs.length}</span>
            ) : null}
          </div>
          {loadState.status === "loading" ? (
            <p role="status" className="loading-state">
              Loading saved BACKTEST configurations...
            </p>
          ) : null}
          {loadState.status === "error" ? (
            <div role="alert" className="error-state">
              {loadState.message}
            </div>
          ) : null}
          {loadState.status === "loaded" && loadState.configs.length === 0 ? (
            <p className="empty-state">
              No saved BACKTEST configurations exist for this workspace.
            </p>
          ) : null}
          {loadState.status === "loaded" && loadState.configs.length > 0 ? (
            <div className="config-list">
              {loadState.configs.map((config) => (
                <article className="config-card" key={config.id}>
                  <div className="section-heading">
                    <h3>{config.name}</h3>
                    <span>{config.mode}</span>
                  </div>
                  <dl className="metadata-grid" aria-label={`${config.name} metadata`}>
                    <MetadataItem label="Instrument" value={config.instrument} />
                    <MetadataItem label="Start" value={config.timeframe_start} />
                    <MetadataItem label="End" value={config.timeframe_end} />
                    <MetadataItem label="Updated" value={config.updated_at} />
                  </dl>
                  <div className="config-actions">
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => handleEdit(config)}
                    >
                      Edit {config.name}
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleCreateDraft(config)}
                      disabled={
                        draftState.status === "creating" &&
                        draftState.configId === config.id
                      }
                    >
                      {draftState.status === "creating" &&
                      draftState.configId === config.id
                        ? "Creating draft..."
                        : `Create draft run from ${config.name}`}
                    </button>
                    {deleteState.status === "confirm" &&
                    deleteState.configId === config.id ? (
                      <>
                        <button
                          className="danger-button"
                          type="button"
                          onClick={() => void confirmDelete(config)}
                        >
                          Confirm delete {config.name}
                        </button>
                        <button
                          className="secondary-button"
                          type="button"
                          onClick={() => setDeleteState({ status: "idle" })}
                        >
                          Cancel delete {config.name}
                        </button>
                      </>
                    ) : (
                      <button
                        className="danger-button"
                        type="button"
                        onClick={() =>
                          setDeleteState({ status: "confirm", configId: config.id })
                        }
                        disabled={
                          deleteState.status === "deleting" &&
                          deleteState.configId === config.id
                        }
                      >
                        {deleteState.status === "deleting" &&
                        deleteState.configId === config.id
                          ? "Deleting..."
                          : `Delete ${config.name}`}
                      </button>
                    )}
                  </div>
                </article>
              ))}
            </div>
          ) : null}
          {deleteState.status === "error" ? (
            <div role="alert" className="inline-alert">
              {deleteState.message}
            </div>
          ) : null}
        </section>
      </section>

      <DraftWorkflowPanel
        draftState={draftState}
        exportState={exportState}
        onRunDataset={handleRunDataset}
        onDownload={handleDownload}
      />
    </main>
  );
}

function DraftWorkflowPanel({
  draftState,
  exportState,
  onRunDataset,
  onDownload,
}: {
  draftState: DraftState;
  exportState: ExportState;
  onRunDataset: (run: BacktestRunShell, configName: string) => void;
  onDownload: (run: BacktestRunShell) => void;
}) {
  if (draftState.status === "idle" || draftState.status === "creating") {
    return null;
  }

  if (draftState.status === "error") {
    return (
      <section className="warnings-panel" aria-label="Draft-from-config result">
        <div role="alert" className="error-state">
          {draftState.message}
        </div>
      </section>
    );
  }

  const run = draftState.run;
  const configName = draftState.configName;
  const isRunning = draftState.status === "running";
  const hasCompletedDataset =
    draftState.status === "completed" || draftState.status === "provider-limited";
  const isProviderLimited = draftState.status === "provider-limited";
  const preview = hasCompletedDataset ? draftState.preview : null;

  return (
    <section className="warnings-panel config-draft-panel" aria-label="Draft-from-config result">
      <div className="section-heading">
        <h2>Draft run from saved configuration</h2>
        <span>{run.status}</span>
      </div>
      <p className="dataset-note">
        Created from {configName}. The run is stored under the same workspace
        BACKTEST workflow as direct draft creation.
      </p>
      <dl className="metadata-grid" aria-label="Draft-from-config metadata">
        <MetadataItem label="Workspace" value={run.workspace_id} />
        <MetadataItem label="Run" value={run.run_id} />
        <MetadataItem label="Instrument" value={run.instrument} />
        <MetadataItem label="Mode" value={run.mode} />
        <MetadataItem label="Start" value={run.timeframe_start} />
        <MetadataItem label="End" value={run.timeframe_end} />
      </dl>
      {!hasCompletedDataset ? (
        <div className="dataset-actions">
          <button
            type="button"
            onClick={() => onRunDataset(run, configName)}
            disabled={isRunning}
          >
            {isRunning
              ? "Running deterministic dataset..."
              : "Run deterministic BACKTEST dataset"}
          </button>
        </div>
      ) : null}
      {isRunning ? (
        <p role="status" className="loading-state">
          Running deterministic BACKTEST dataset...
        </p>
      ) : null}
      {preview ? (
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
              {draftState.message}
            </div>
          ) : (
            <>
              <p className="quality-link-note">
                <a href={run.quality_report_path ?? "#"}>Quality route</a> is
                available for this completed dataset. Movement fields remain
                pending price enrichment.
              </p>
              <div className="dataset-actions export-actions">
                <button
                  type="button"
                  onClick={() => onDownload(run)}
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
            </>
          )}
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
        </section>
      ) : null}
    </section>
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

function configRequest(formState: ConfigFormState): CreateBacktestConfigRequest {
  return {
    name: formState.name.trim(),
    instrument: "BTCUSD",
    mode: "BACKTEST",
    timeframe_start: formState.timeframeStart,
    timeframe_end: formState.timeframeEnd,
  };
}

function validateForm(formState: ConfigFormState): string | null {
  if (!formState.name.trim()) {
    return "Configuration name is required.";
  }

  const start = parseIsoTimestamp(formState.timeframeStart);
  const end = parseIsoTimestamp(formState.timeframeEnd);

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

  return "Saved BACKTEST configuration request failed.";
}

function isDatasetRunPreview(value: unknown): value is DatasetRunPreview {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<DatasetRunPreview>;
  return Boolean(candidate.summary && Array.isArray(candidate.records));
}
