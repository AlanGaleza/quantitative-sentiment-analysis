import type { AuthErrorBody, AuthSessionResponse, LoginRequest } from "./types";

const API_PREFIX = "/api";

export class AuthApiError extends Error {
  readonly status: number;
  readonly detail: string;
  readonly payload: unknown;

  constructor(status: number, detail: string, payload?: unknown) {
    super(detail);
    this.name = "AuthApiError";
    this.status = status;
    this.detail = detail;
    this.payload = payload;
  }
}

export function buildLoginUrl(): string {
  return withApiBaseUrl(`${API_PREFIX}/auth/login`);
}

export function buildLogoutUrl(): string {
  return withApiBaseUrl(`${API_PREFIX}/auth/logout`);
}

export function buildCurrentUserUrl(): string {
  return withApiBaseUrl(`${API_PREFIX}/auth/me`);
}

export async function loginWithPassword(
  request: LoginRequest,
): Promise<AuthSessionResponse> {
  const response = await fetch(buildLoginUrl(), {
    method: "POST",
    credentials: "include",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new AuthApiError(response.status, await readErrorDetail(response));
  }

  return readJson<AuthSessionResponse>(
    response,
    "Login response was empty.",
  );
}

export async function logoutSession(): Promise<void> {
  const response = await fetch(buildLogoutUrl(), {
    method: "POST",
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new AuthApiError(response.status, await readErrorDetail(response));
  }
}

export async function fetchCurrentSession(): Promise<AuthSessionResponse> {
  const response = await fetch(buildCurrentUserUrl(), {
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new AuthApiError(response.status, await readErrorDetail(response));
  }

  return readJson<AuthSessionResponse>(
    response,
    "Current user response was empty.",
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
    throw new AuthApiError(response.status, emptyDetail);
  }

  try {
    return JSON.parse(text) as T;
  } catch (error) {
    throw new AuthApiError(
      response.status,
      "Auth response was not valid JSON.",
      error,
    );
  }
}

async function readErrorDetail(response: Response): Promise<string> {
  const text = await response.text();

  if (!text.trim()) {
    return `Auth request failed with status ${response.status}`;
  }

  try {
    const body = JSON.parse(text) as AuthErrorBody;
    if (typeof body.detail === "string" && body.detail.length > 0) {
      return body.detail;
    }
  } catch {
    // Fall through to a deterministic generic message.
  }

  return `Auth request failed with status ${response.status}`;
}
