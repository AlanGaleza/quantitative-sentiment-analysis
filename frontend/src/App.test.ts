import { describe, expect, it } from "vitest";

import { parseQualityRoute } from "./App";

describe("parseQualityRoute", () => {
  it("returns the run-scoped quality route", () => {
    expect(parseQualityRoute("/workspaces/workspace-alpha/backtests/run-001/quality")).toEqual({
      workspaceId: "workspace-alpha",
      runId: "run-001",
    });
  });

  it("returns null for malformed encoded route segments", () => {
    expect(parseQualityRoute("/workspaces/%E0%A4%A/backtests/run-001/quality")).toBeNull();
  });
});
