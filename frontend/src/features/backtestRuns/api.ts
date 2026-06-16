import type { BacktestRunHistoryResponse } from "./types";

const API_PREFIX = "/api";

export class BacktestRunHistoryApiError extends Error {
  readonly status: number;
  readonly detail: string;
  readonly payload: unknown;

  constructor(status: number, detail: string, payload?: unknown) {
    super(detail);
    this.name = "BacktestRunHistoryApiError";
    this.status = status;
    this.detail = detail;
    this.payload = payload;
  }
}

export function buildBacktestRunHistoryUrl(workspaceId: string): string {
  return withApiBaseUrl(
    `${API_PREFIX}/workspaces/${encodeURIComponent(workspaceId)}/backtests`,
  );
}

export async function fetchBacktestRunHistory(
  workspaceId: string,
): Promise<BacktestRunHistoryResponse> {
  const response = await fetch(buildBacktestRunHistoryUrl(workspaceId), {
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new BacktestRunHistoryApiError(
      response.status,
      await readErrorDetail(response),
    );
  }

  return readJson<BacktestRunHistoryResponse>(
    response,
    "BACKTEST run history response was empty.",
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
    throw new BacktestRunHistoryApiError(response.status, emptyDetail);
  }

  try {
    return JSON.parse(text) as T;
  } catch (error) {
    throw new BacktestRunHistoryApiError(
      response.status,
      "BACKTEST run history response was not valid JSON.",
      error,
    );
  }
}

async function readErrorDetail(response: Response): Promise<string> {
  const text = await response.text();

  if (!text.trim()) {
    return `BACKTEST run history request failed with status ${response.status}`;
  }

  try {
    const body = JSON.parse(text) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.length > 0) {
      return body.detail;
    }
  } catch {
    // Fall through to a deterministic generic message.
  }

  return `BACKTEST run history request failed with status ${response.status}`;
}
