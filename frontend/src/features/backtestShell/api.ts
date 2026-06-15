import type {
  BacktestRunShell,
  CreateBacktestRunRequest,
  DatasetRunPreview,
} from "./types";

const API_PREFIX = "/api";

export class BacktestShellApiError extends Error {
  readonly status: number;
  readonly detail: string;
  readonly payload: unknown;

  constructor(status: number, detail: string, payload?: unknown) {
    super(detail);
    this.name = "BacktestShellApiError";
    this.status = status;
    this.detail = detail;
    this.payload = payload;
  }
}

export function buildCreateBacktestRunUrl(workspaceId: string): string {
  return withApiBaseUrl(
    `${API_PREFIX}/workspaces/${encodeURIComponent(workspaceId)}/backtests/drafts`,
  );
}

export function buildBacktestRunShellUrl(
  workspaceId: string,
  runId: string,
): string {
  return withApiBaseUrl(
    `${API_PREFIX}/workspaces/${encodeURIComponent(
      workspaceId,
    )}/backtests/${encodeURIComponent(runId)}`,
  );
}

export function buildRunBacktestDatasetUrl(
  workspaceId: string,
  runId: string,
): string {
  return withApiBaseUrl(
    `${API_PREFIX}/workspaces/${encodeURIComponent(
      workspaceId,
    )}/backtests/${encodeURIComponent(runId)}/dataset/run`,
  );
}

export function buildBacktestDatasetUrl(
  workspaceId: string,
  runId: string,
): string {
  return withApiBaseUrl(
    `${API_PREFIX}/workspaces/${encodeURIComponent(
      workspaceId,
    )}/backtests/${encodeURIComponent(runId)}/dataset`,
  );
}

export async function createBacktestRunShell(
  workspaceId: string,
  request: CreateBacktestRunRequest,
): Promise<BacktestRunShell> {
  const response = await fetch(buildCreateBacktestRunUrl(workspaceId), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new BacktestShellApiError(response.status, await readErrorDetail(response));
  }

  return (await response.json()) as BacktestRunShell;
}

export async function runBacktestDataset(
  workspaceId: string,
  runId: string,
): Promise<DatasetRunPreview> {
  const response = await fetch(buildRunBacktestDatasetUrl(workspaceId, runId), {
    method: "POST",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    const error = await readError(response);
    throw new BacktestShellApiError(response.status, error.detail, error.payload);
  }

  return (await response.json()) as DatasetRunPreview;
}

export async function fetchBacktestDataset(
  workspaceId: string,
  runId: string,
): Promise<DatasetRunPreview> {
  const response = await fetch(buildBacktestDatasetUrl(workspaceId, runId), {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    const error = await readError(response);
    throw new BacktestShellApiError(response.status, error.detail, error.payload);
  }

  return (await response.json()) as DatasetRunPreview;
}

export async function fetchBacktestRunShell(
  workspaceId: string,
  runId: string,
): Promise<BacktestRunShell> {
  const response = await fetch(buildBacktestRunShellUrl(workspaceId, runId), {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new BacktestShellApiError(response.status, await readErrorDetail(response));
  }

  return (await response.json()) as BacktestRunShell;
}

function withApiBaseUrl(path: string): string {
  const baseUrl = import.meta.env.VITE_API_BASE_URL?.trim();

  if (!baseUrl) {
    return path;
  }

  return `${baseUrl.replace(/\/+$/, "")}${path}`;
}

async function readErrorDetail(response: Response): Promise<string> {
  return (await readError(response)).detail;
}

async function readError(
  response: Response,
): Promise<{ detail: string; payload?: unknown }> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.length > 0) {
      return { detail: body.detail, payload: body.detail };
    }
    if (isDatasetPreview(body.detail)) {
      return {
        detail: datasetPreviewErrorMessage(body.detail),
        payload: body.detail,
      };
    }
  } catch {
    // Fall through to a deterministic generic message.
  }

  return { detail: `BACKTEST shell request failed with status ${response.status}` };
}

function isDatasetPreview(value: unknown): value is DatasetRunPreview {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<DatasetRunPreview>;
  return Boolean(candidate.summary && Array.isArray(candidate.records));
}

function datasetPreviewErrorMessage(preview: DatasetRunPreview): string {
  const limitation = preview.summary.provider_limitation;
  if (limitation) {
    return [limitation.provider_name, limitation.reason, limitation.detail]
      .filter(Boolean)
      .join(": ");
  }
  return `BACKTEST dataset request failed with status ${preview.summary.status}`;
}
