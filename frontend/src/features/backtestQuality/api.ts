import type { BacktestQualityReport } from "./types";

const API_PREFIX = "/api";

export class QualityReportApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "QualityReportApiError";
    this.status = status;
    this.detail = detail;
  }
}

export function buildBacktestQualityReportUrl(
  workspaceId: string,
  runId: string,
): string {
  const path = `${API_PREFIX}/workspaces/${encodeURIComponent(
    workspaceId,
  )}/backtests/${encodeURIComponent(runId)}/quality`;
  const baseUrl = import.meta.env.VITE_API_BASE_URL?.trim();

  if (!baseUrl) {
    return path;
  }

  return `${baseUrl.replace(/\/+$/, "")}${path}`;
}

export async function fetchBacktestQualityReport(
  workspaceId: string,
  runId: string,
): Promise<BacktestQualityReport> {
  const response = await fetch(buildBacktestQualityReportUrl(workspaceId, runId), {
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new QualityReportApiError(response.status, await readErrorDetail(response));
  }

  return readJson<BacktestQualityReport>(
    response,
    "Quality report response was empty.",
  );
}

async function readJson<T>(response: Response, emptyDetail: string): Promise<T> {
  const text = await response.text();

  if (!text.trim()) {
    throw new QualityReportApiError(response.status, emptyDetail);
  }

  try {
    return JSON.parse(text) as T;
  } catch {
    throw new QualityReportApiError(
      response.status,
      "Quality report response was not valid JSON.",
    );
  }
}

async function readErrorDetail(response: Response): Promise<string> {
  const text = await response.text();

  if (!text.trim()) {
    return `Quality report request failed with status ${response.status}`;
  }

  try {
    const body = JSON.parse(text) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.length > 0) {
      return body.detail;
    }
  } catch {
    // Fall through to a deterministic generic message.
  }

  return `Quality report request failed with status ${response.status}`;
}
