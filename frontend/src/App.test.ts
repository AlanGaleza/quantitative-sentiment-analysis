import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createElement, type ComponentType } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App, {
  defaultWorkspacePath,
  parseAppRoute,
  parseConfigRoute,
  parseHistoryRoute,
  parseQualityRoute,
  parseShellRoute,
} from "./App";
import type { AuthSessionResponse } from "./features/auth/types";

type TestAppProps = {
  loadCurrentSession?: () => Promise<AuthSessionResponse>;
  logout?: () => Promise<void>;
};

const TestApp = App as ComponentType<TestAppProps>;

describe("parseAppRoute", () => {
  it("returns the workspace config route", () => {
    expect(parseAppRoute("/workspaces/workspace-alpha/backtest-configs")).toEqual({
      kind: "configs",
      workspaceId: "workspace-alpha",
    });
    expect(parseConfigRoute("/workspaces/workspace-alpha/backtest-configs")).toEqual({
      kind: "configs",
      workspaceId: "workspace-alpha",
    });
  });

  it("returns the workspace shell route", () => {
    expect(parseAppRoute("/workspaces/workspace-alpha/backtests/new")).toEqual({
      kind: "shell",
      workspaceId: "workspace-alpha",
    });
  });

  it("returns the workspace run history route", () => {
    expect(parseAppRoute("/workspaces/workspace-alpha/backtests")).toEqual({
      kind: "history",
      workspaceId: "workspace-alpha",
    });
    expect(parseHistoryRoute("/workspaces/workspace-alpha/backtests")).toEqual({
      kind: "history",
      workspaceId: "workspace-alpha",
    });
  });

  it("returns the run-scoped quality route", () => {
    expect(parseAppRoute("/workspaces/workspace-alpha/backtests/run-001/quality")).toEqual({
      kind: "quality",
      workspaceId: "workspace-alpha",
      runId: "run-001",
    });
  });

  it("prioritizes the shell route so new is not treated as a run ID", () => {
    expect(parseShellRoute("/workspaces/workspace-alpha/backtests/new")).toEqual({
      kind: "shell",
      workspaceId: "workspace-alpha",
    });
    expect(parseQualityRoute("/workspaces/workspace-alpha/backtests/new")).toBeNull();
  });

  it("returns null for malformed encoded route segments", () => {
    expect(parseAppRoute("/workspaces/%E0%A4%A/backtest-configs")).toBeNull();
    expect(parseAppRoute("/workspaces/%E0%A4%A/backtests")).toBeNull();
    expect(parseAppRoute("/workspaces/%E0%A4%A/backtests/new")).toBeNull();
    expect(parseAppRoute("/workspaces/%E0%A4%A/backtests/run-001/quality")).toBeNull();
  });
});

describe("defaultWorkspacePath", () => {
  it("points authenticated users to run history", () => {
    expect(defaultWorkspacePath(authSession())).toBe(
      "/workspaces/workspace-alpha/backtests",
    );
  });
});

describe("App", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    window.history.pushState({}, "", "/");
  });

  it("shows login for protected workspace routes when session bootstrap fails", async () => {
    window.history.pushState({}, "", "/workspaces/workspace-alpha/backtests/new");

    render(
      createElement(TestApp, {
        loadCurrentSession: async () => {
          throw new Error("not authenticated");
        },
      }),
    );

    expect(await screen.findByRole("heading", { name: "Workspace login" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });

  it("renders the workspace shell page for authenticated users", async () => {
    window.history.pushState({}, "", "/workspaces/workspace-alpha/backtests/new");

    render(
      createElement(TestApp, {
        loadCurrentSession: async () => authSession(),
      }),
    );

    expect(
      await screen.findByRole("heading", { name: "Workspace backtest shell" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Workspace")).toHaveValue("workspace-alpha");
    expect(screen.getByRole("link", { name: "Run history" })).toHaveAttribute(
      "href",
      "/workspaces/workspace-alpha/backtests",
    );
    expect(screen.getByRole("link", { name: "Saved configs" })).toHaveAttribute(
      "href",
      "/workspaces/workspace-alpha/backtest-configs",
    );
    expect(screen.getByRole("button", { name: "Log out" })).toBeInTheDocument();
  });

  it("renders run history after auth bootstrap", async () => {
    window.history.pushState({}, "", "/workspaces/workspace-alpha/backtests");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ workspace_id: "workspace-alpha", runs: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(
      createElement(TestApp, {
        loadCurrentSession: async () => authSession(),
      }),
    );

    expect(
      await screen.findByRole("heading", { name: "BACKTEST run history" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("No BACKTEST runs exist for this workspace yet."),
    ).toBeInTheDocument();
  });

  it("renders saved configurations after auth bootstrap", async () => {
    window.history.pushState({}, "", "/workspaces/workspace-alpha/backtest-configs");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(
      createElement(TestApp, {
        loadCurrentSession: async () => authSession(),
      }),
    );

    expect(
      await screen.findByRole("heading", {
        name: "Saved BACKTEST configurations",
      }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText(
        "No saved BACKTEST configurations exist for this workspace.",
      ),
    ).toBeInTheDocument();
  });

  it("logs in and navigates to the default workspace run history", async () => {
    window.history.pushState({}, "", "/login");
    const session = authSession();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify(session), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ workspace_id: "workspace-alpha", runs: [] }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(
      createElement(TestApp, {
        loadCurrentSession: async () => {
          throw new Error("not authenticated");
        },
      }),
    );

    fireEvent.change(await screen.findByLabelText("Email"), {
      target: { value: "trader@example.test" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "secret-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(window.location.pathname).toBe(
        "/workspaces/workspace-alpha/backtests",
      );
    });
    expect(
      await screen.findByRole("heading", { name: "BACKTEST run history" }),
    ).toBeInTheDocument();
  });
});

function authSession(): AuthSessionResponse {
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
