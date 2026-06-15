import { expect, test, type Page } from "@playwright/test";

// Seed exemplar for /10x-e2e generation.
// Risk: context/foundation/test-plan.md #6.
// Boundary: real browser route and UI; the draft API is mocked here so this
// seed protects semantic UI copy without creating persistent backend data.

test.describe("seed: BACKTEST shell semantic safety", () => {
  test("risk #6: quality route gate stays BACKTEST-only and non-advisory before dataset completion", async ({
    page,
  }) => {
    const uniqueWorkspaceId = `e2e-seed-${Date.now()}-${test.info().parallelIndex}`;
    const runId = `${uniqueWorkspaceId}-draft-run`;
    const qualityPath = `/workspaces/${encodeURIComponent(
      uniqueWorkspaceId,
    )}/backtests/${encodeURIComponent(runId)}/quality`;
    const draftApiRoute = `**/api/workspaces/${encodeURIComponent(
      uniqueWorkspaceId,
    )}/backtests/drafts`;

    await page.route(draftApiRoute, async (route, request) => {
      expect(request.method()).toBe("POST");
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          workspace_id: uniqueWorkspaceId,
          run_id: runId,
          instrument: "BTCUSD",
          mode: "BACKTEST",
          timeframe_start: "2026-06-01T00:00:00.000Z",
          timeframe_end: "2026-06-08T00:00:00.000Z",
          status: "DRAFT",
          created_at: "2026-06-15T10:00:00.000Z",
          quality_report_path: qualityPath,
        }),
      });
    });

    try {
      await page.goto(`/workspaces/${encodeURIComponent(uniqueWorkspaceId)}/backtests/new`);

      await expect(
        page.getByRole("heading", { name: "Workspace backtest shell" }),
      ).toBeVisible();
      await expect(page.getByRole("textbox", { name: "Workspace" })).toHaveValue(
        uniqueWorkspaceId,
      );
      await expect(
        page.getByText(/historical BTCUSD directional bias datasets/i),
      ).toBeVisible();

      await page
        .getByRole("textbox", { name: "Timeframe start" })
        .fill("2026-06-01T00:00:00.000Z");
      await page
        .getByRole("textbox", { name: "Timeframe end" })
        .fill("2026-06-08T00:00:00.000Z");

      const draftCreated = page.waitForResponse(
        (response) =>
          response.url().includes(`/api/workspaces/${uniqueWorkspaceId}/backtests/drafts`) &&
          response.request().method() === "POST" &&
          response.ok(),
      );
      await page.getByRole("button", { name: "Create draft run" }).click();
      await draftCreated;

      await expect(
        page.getByRole("heading", { name: "Draft run created" }),
      ).toBeVisible();
      await expect(page.getByRole("link", { name: "Quality route" })).toHaveAttribute(
        "href",
        qualityPath,
      );
      await expect(
        page.getByText(
          /unavailable until this BACKTEST run has a completed deterministic dataset/i,
        ),
      ).toBeVisible();
      await expect(
        page.getByRole("button", { name: "Run deterministic BACKTEST dataset" }),
      ).toBeVisible();

      await expect(page.getByText(/S-02/i)).toHaveCount(0);
      await expect(page.getByText(/CryptoPanic/i)).toHaveCount(0);
      await expect(
        page.getByText(
          /trading signal|buy recommendation|sell recommendation|investment recommendation|broker integration|place order/i,
        ),
      ).toHaveCount(0);
    } finally {
      await cleanupSeedState(page, draftApiRoute);
    }
  });
});

async function cleanupSeedState(page: Page, draftApiRoute: string): Promise<void> {
  await page.unroute(draftApiRoute).catch(() => undefined);
  await page
    .evaluate(() => {
      window.localStorage.clear();
      window.sessionStorage.clear();
    })
    .catch(() => undefined);
  await page.context().clearCookies();
}
