import { render, screen } from "@testing-library/react";
import { createElement } from "react";
import { describe, expect, it } from "vitest";

import App, { parseAppRoute, parseQualityRoute, parseShellRoute } from "./App";

describe("parseAppRoute", () => {
  it("returns the workspace shell route", () => {
    expect(parseAppRoute("/workspaces/workspace-alpha/backtests/new")).toEqual({
      kind: "shell",
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
    expect(parseAppRoute("/workspaces/%E0%A4%A/backtests/new")).toBeNull();
    expect(parseAppRoute("/workspaces/%E0%A4%A/backtests/run-001/quality")).toBeNull();
  });
});

describe("parseQualityRoute", () => {
  it("returns the run-scoped quality route", () => {
    expect(parseQualityRoute("/workspaces/workspace-alpha/backtests/run-001/quality")).toEqual({
      kind: "quality",
      workspaceId: "workspace-alpha",
      runId: "run-001",
    });
  });

  it("returns null for malformed encoded route segments", () => {
    expect(parseQualityRoute("/workspaces/%E0%A4%A/backtests/run-001/quality")).toBeNull();
  });
});

describe("App", () => {
  it("renders the workspace shell page for the new route", () => {
    window.history.pushState({}, "", "/workspaces/workspace-alpha/backtests/new");

    render(createElement(App));

    expect(
      screen.getByRole("heading", { name: "Workspace backtest shell" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Workspace")).toHaveValue("workspace-alpha");
  });
});
