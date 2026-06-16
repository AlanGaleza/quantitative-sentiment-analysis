import type { BacktestRunShell } from "../backtestShell/types";

const API_PREFIX = "/api";

export interface BacktestConfig {
  id: string;
  workspace_id: string;
  name: string;
  instrument: "BTCUSD";
  mode: "BACKTEST";
  timeframe_start: string;
  timeframe_end: string;
  created_at: string;
  updated_at: string;
}

export interface CreateBacktestConfigRequest {
  name: string;
  instrument: "BTCUSD";
  mode: "BACKTEST";
  timeframe_start: string;
  timeframe_end: string;
}

export interface UpdateBacktestConfigRequest {
  name?: string;
  instrument?: "BTCUSD";
  mode?: "BACKTEST";
  timeframe_start?: string;
  timeframe_end?: string;
}

export class BacktestConfigApiError extends Error {
  readonly status: number;
  readonly detail: string;
  readonly payload: unknown;

  constructor(status: number, detail: string, payload?: unknown) {
    super(detail);
    this.name = "BacktestConfigApiError";
    this.status = status;
    this.detail = detail;
    this.payload = payload;
  }
}

export function buildBacktestConfigListUrl(workspaceId: string): string {
  return withApiBaseUrl(
    `${API_PREFIX}/workspaces/${encodeURIComponent(workspaceId)}/backtest-configs`,
  );
}

export function buildBacktestConfigDetailUrl(
  workspaceId: string,
  configId: string,
): string {
  return withApiBaseUrl(
    `${API_PREFIX}/workspaces/${encodeURIComponent(
      workspaceId,
    )}/backtest-configs/${encodeURIComponent(configId)}`,
  );
}

export function buildBacktestConfigDraftUrl(
  workspaceId: string,
  configId: string,
): string {
  return withApiBaseUrl(
    `${API_PREFIX}/workspaces/${encodeURIComponent(
      workspaceId,
    )}/backtest-configs/${encodeURIComponent(configId)}/drafts`,
  );
}

export async function listBacktestConfigs(
  workspaceId: string,
): Promise<BacktestConfig[]> {
  const response = await fetch(buildBacktestConfigListUrl(workspaceId), {
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new BacktestConfigApiError(
      response.status,
      await readErrorDetail(response),
    );
  }

  return readJson<BacktestConfig[]>(
    response,
    "Saved BACKTEST configuration list response was empty.",
  );
}

export async function createBacktestConfig(
  workspaceId: string,
  request: CreateBacktestConfigRequest,
): Promise<BacktestConfig> {
  const response = await fetch(buildBacktestConfigListUrl(workspaceId), {
    method: "POST",
    credentials: "include",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new BacktestConfigApiError(
      response.status,
      await readErrorDetail(response),
    );
  }

  return readJson<BacktestConfig>(
    response,
    "Saved BACKTEST configuration create response was empty.",
  );
}

export async function updateBacktestConfig(
  workspaceId: string,
  configId: string,
  request: UpdateBacktestConfigRequest,
): Promise<BacktestConfig> {
  const response = await fetch(
    buildBacktestConfigDetailUrl(workspaceId, configId),
    {
      method: "PUT",
      credentials: "include",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    },
  );

  if (!response.ok) {
    throw new BacktestConfigApiError(
      response.status,
      await readErrorDetail(response),
    );
  }

  return readJson<BacktestConfig>(
    response,
    "Saved BACKTEST configuration update response was empty.",
  );
}

export async function deleteBacktestConfig(
  workspaceId: string,
  configId: string,
): Promise<void> {
  const response = await fetch(
    buildBacktestConfigDetailUrl(workspaceId, configId),
    {
      method: "DELETE",
      credentials: "include",
      headers: {
        Accept: "application/json",
      },
    },
  );

  if (!response.ok) {
    throw new BacktestConfigApiError(
      response.status,
      await readErrorDetail(response),
    );
  }
}

export async function createDraftFromBacktestConfig(
  workspaceId: string,
  configId: string,
): Promise<BacktestRunShell> {
  const response = await fetch(buildBacktestConfigDraftUrl(workspaceId, configId), {
    method: "POST",
    credentials: "include",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({}),
  });

  if (!response.ok) {
    throw new BacktestConfigApiError(
      response.status,
      await readErrorDetail(response),
    );
  }

  return readJson<BacktestRunShell>(
    response,
    "Draft-from-config response was empty.",
  );
}

function withApiBaseUrl(path: string): string {
  const baseUrl = import.meta.env.VITE_API_BASE_URL?.trim();

  if (!baseUrl) {
    return path;
  }

  return `${baseUrl.replace(/\/+$/, "")}${path}`;
}

async function readJson<T>(response: Response, emptyDetail: string): Promise<T> {
  const text = await response.text();

  if (!text.trim()) {
    throw new BacktestConfigApiError(response.status, emptyDetail);
  }

  try {
    return JSON.parse(text) as T;
  } catch (error) {
    throw new BacktestConfigApiError(
      response.status,
      "Saved BACKTEST configuration response was not valid JSON.",
      error,
    );
  }
}

async function readErrorDetail(response: Response): Promise<string> {
  const text = await response.text();

  if (!text.trim()) {
    return `Saved BACKTEST configuration request failed with status ${response.status}`;
  }

  try {
    const body = JSON.parse(text) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.length > 0) {
      return body.detail;
    }
  } catch {
    // Fall through to a deterministic generic message.
  }

  return `Saved BACKTEST configuration request failed with status ${response.status}`;
}
