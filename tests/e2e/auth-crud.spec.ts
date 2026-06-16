import { expect, test, type Page } from "@playwright/test";

const E2E_EMAIL = process.env.QSA_E2E_USER_EMAIL ?? "e2e-trader@example.test";
const E2E_PASSWORD =
  process.env.QSA_E2E_USER_PASSWORD ?? "e2e-correct-password";
const E2E_WORKSPACE =
  process.env.QSA_E2E_WORKSPACE_SLUG ?? "demo-workspace";

test.describe("auth plus saved BACKTEST configuration CRUD", () => {
  test("risk access-control/CRUD: logged-in user owns saved config lifecycle and draft creation", async ({
    baseURL,
    page,
  }) => {
    const uniqueSuffix = `${Date.now()}-${test.info().parallelIndex}`;
    const originalName = `E2E BACKTEST config ${uniqueSuffix}`;
    const renamedName = `E2E BACKTEST config renamed ${uniqueSuffix}`;
    const timeframeStart = "2026-06-01T00:00:00.000Z";
    const timeframeEnd = "2026-06-08T00:00:00.000Z";
    let configId: string | null = null;
    let configDeleted = false;
    let loggedOut = false;

    try {
      await page.goto("/login");
      await expect(
        page.getByRole("heading", { name: "Workspace login" }),
      ).toBeVisible();

      await page.getByLabel("Email").fill(E2E_EMAIL);
      await page.getByLabel("Password").fill(E2E_PASSWORD);

      const loginResponse = page.waitForResponse(
        (response) =>
          response.url().includes("/api/auth/login") &&
          response.request().method() === "POST" &&
          response.ok(),
      );
      await page.getByRole("button", { name: "Sign in" }).click();
      await loginResponse;

      await expect(page).toHaveURL(
        new RegExp(`/workspaces/${E2E_WORKSPACE}/backtests/?$`),
      );
      await expect(
        page.getByRole("heading", { name: "BACKTEST run history" }),
      ).toBeVisible();

      await page.getByRole("link", { name: "Saved configs" }).click();

      await expect(page).toHaveURL(
        new RegExp(`/workspaces/${E2E_WORKSPACE}/backtest-configs/?$`),
      );
      await expect(
        page.getByRole("heading", { name: "Saved BACKTEST configurations" }),
      ).toBeVisible();

      await page.getByLabel("Configuration name").fill(originalName);
      await page.getByLabel("Timeframe start").fill(timeframeStart);
      await page.getByLabel("Timeframe end").fill(timeframeEnd);

      const createResponsePromise = page.waitForResponse(
        (response) =>
          response.url().includes(
            `/api/workspaces/${E2E_WORKSPACE}/backtest-configs`,
          ) &&
          response.request().method() === "POST" &&
          response.ok(),
      );
      await page.getByRole("button", { name: "Create configuration" }).click();
      const createResponse = await createResponsePromise;
      const createdConfig = (await createResponse.json()) as { id: string };
      configId = createdConfig.id;

      await expect(
        page.getByRole("heading", { name: originalName }),
      ).toBeVisible();

      await page.getByRole("button", { name: `Edit ${originalName}` }).click();
      await expect(page.getByLabel("Configuration name")).toHaveValue(originalName);
      await page.getByLabel("Configuration name").fill(renamedName);

      const updateResponse = page.waitForResponse(
        (response) =>
          response.url().includes(
            `/api/workspaces/${E2E_WORKSPACE}/backtest-configs/${configId}`,
          ) &&
          response.request().method() === "PUT" &&
          response.ok(),
      );
      await page.getByRole("button", { name: "Save configuration" }).click();
      await updateResponse;

      await expect(
        page.getByRole("heading", { name: renamedName }),
      ).toBeVisible();

      const draftResponse = page.waitForResponse(
        (response) =>
          response.url().includes(
            `/api/workspaces/${E2E_WORKSPACE}/backtest-configs/${configId}/drafts`,
          ) &&
          response.request().method() === "POST" &&
          response.ok(),
      );
      await page
        .getByRole("button", { name: `Create draft run from ${renamedName}` })
        .click();
      await draftResponse;

      await expect(
        page.getByRole("heading", { name: "Draft run from saved configuration" }),
      ).toBeVisible();
      await expect(
        page.getByText(`Created from ${renamedName}.`, { exact: false }),
      ).toBeVisible();

      const deleteResponse = page.waitForResponse(
        (response) =>
          response.url().includes(
            `/api/workspaces/${E2E_WORKSPACE}/backtest-configs/${configId}`,
          ) &&
          response.request().method() === "DELETE" &&
          response.ok(),
      );
      await page.getByRole("button", { name: `Delete ${renamedName}` }).click();
      await page
        .getByRole("button", { name: `Confirm delete ${renamedName}` })
        .click();
      await deleteResponse;
      configDeleted = true;

      await expect(
        page.getByRole("heading", { name: renamedName }),
      ).toHaveCount(0);

      const logoutResponse = page.waitForResponse(
        (response) =>
          response.url().includes("/api/auth/logout") &&
          response.request().method() === "POST" &&
          response.ok(),
      );
      await page.getByRole("button", { name: "Log out" }).click();
      await logoutResponse;
      loggedOut = true;
      await expect(
        page.getByRole("heading", { name: "Workspace login" }),
      ).toBeVisible();
    } finally {
      await cleanup(page, baseURL, configId, configDeleted, loggedOut);
    }
  });
});

async function cleanup(
  page: Page,
  baseURL: string | undefined,
  configId: string | null,
  configDeleted: boolean,
  loggedOut: boolean,
): Promise<void> {
  const origin = new URL(baseURL ?? "http://127.0.0.1:3100").origin;

  if (configId && !configDeleted) {
    await page.request
      .delete(`/api/workspaces/${E2E_WORKSPACE}/backtest-configs/${configId}`, {
        headers: {
          Accept: "application/json",
          Origin: origin,
        },
      })
      .catch(() => undefined);
  }

  if (!loggedOut) {
    await page.request
      .post("/api/auth/logout", {
        headers: {
          Accept: "application/json",
          Origin: origin,
        },
      })
      .catch(() => undefined);
  }

  await page.context().clearCookies();
}
