import type { BacktestRunShell, CreateBacktestRunRequest } from "./types";

const API_PREFIX = "/api";

export class BacktestShellApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "BacktestShellApiError";
    this.status = status;
    this.detail = detail;
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
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.length > 0) {
      return body.detail;
    }
  } catch {
    // Fall through to a deterministic generic message.
  }

  return `BACKTEST shell request failed with status ${response.status}`;
}
