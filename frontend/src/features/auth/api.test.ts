import { afterEach, describe, expect, it, vi } from "vitest";

import {
  AuthApiError,
  buildCurrentUserUrl,
  buildLoginUrl,
  buildLogoutUrl,
  fetchCurrentSession,
  loginWithPassword,
  logoutSession,
} from "./api";

describe("auth API client", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("uses VITE_API_BASE_URL when set", () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test/");

    expect(buildLoginUrl()).toBe("https://api.example.test/api/auth/login");
    expect(buildLogoutUrl()).toBe("https://api.example.test/api/auth/logout");
    expect(buildCurrentUserUrl()).toBe("https://api.example.test/api/auth/me");
  });

  it("falls back to relative /api for local Vite proxy development", () => {
    vi.stubEnv("VITE_API_BASE_URL", "");

    expect(buildLoginUrl()).toBe("/api/auth/login");
    expect(buildLogoutUrl()).toBe("/api/auth/logout");
    expect(buildCurrentUserUrl()).toBe("/api/auth/me");
  });

  it("posts JSON credentials and includes cookies when logging in", async () => {
    const session = authSession();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(session), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      loginWithPassword({
        email: "trader@example.test",
        password: "secret-password",
      }),
    ).resolves.toEqual(session);

    expect(fetchMock).toHaveBeenCalledWith("/api/auth/login", {
      method: "POST",
      credentials: "include",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email: "trader@example.test",
        password: "secret-password",
      }),
    });
  });

  it("loads the current session with cookies", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(authSession()), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchCurrentSession();

    expect(fetchMock).toHaveBeenCalledWith("/api/auth/me", {
      credentials: "include",
      headers: {
        Accept: "application/json",
      },
    });
  });

  it("logs out with cookies and accepts an empty backend response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(logoutSession()).resolves.toBeUndefined();

    expect(fetchMock).toHaveBeenCalledWith("/api/auth/logout", {
      method: "POST",
      credentials: "include",
      headers: {
        Accept: "application/json",
      },
    });
  });

  it("raises typed errors for non-2xx auth responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "not authenticated" }), {
          status: 401,
          headers: { "content-type": "application/json" },
        }),
      ),
    );

    await expect(fetchCurrentSession()).rejects.toMatchObject({
      status: 401,
      detail: "not authenticated",
    } satisfies Partial<AuthApiError>);
  });

  it("raises typed errors for empty successful JSON responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 200 })),
    );

    await expect(fetchCurrentSession()).rejects.toMatchObject({
      status: 200,
      detail: "Current user response was empty.",
    } satisfies Partial<AuthApiError>);
  });
});

function authSession() {
  return {
    user: {
      id: "user-001",
      email: "trader@example.test",
    },
    workspaces: [
      {
        id: "workspace-001",
        slug: "workspace-alpha",
        name: "Workspace Alpha",
      },
    ],
    default_workspace_slug: "workspace-alpha",
  };
}
