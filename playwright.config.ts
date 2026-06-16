import { defineConfig, devices } from "@playwright/test";

const frontendHost = process.env.PLAYWRIGHT_HOST ?? "127.0.0.1";
const frontendPort = process.env.PLAYWRIGHT_PORT ?? "3100";
const apiHost = process.env.PLAYWRIGHT_API_HOST ?? "127.0.0.1";
const apiPort = process.env.PLAYWRIGHT_API_PORT ?? "8000";
const baseURL =
  process.env.PLAYWRIGHT_BASE_URL ??
  `http://${frontendHost}:${frontendPort}`;
const apiURL =
  process.env.PLAYWRIGHT_API_BASE_URL ?? `http://${apiHost}:${apiPort}`;
const reuseExistingServer =
  process.env.PLAYWRIGHT_REUSE_SERVER === "1" && !process.env.CI;

const e2eEmail =
  process.env.QSA_E2E_USER_EMAIL ?? "e2e-trader@example.test";
const e2ePassword =
  process.env.QSA_E2E_USER_PASSWORD ?? "e2e-correct-password";
const e2eWorkspaceSlug =
  process.env.QSA_E2E_WORKSPACE_SLUG ?? "demo-workspace";
const e2eWorkspaceName =
  process.env.QSA_E2E_WORKSPACE_NAME ?? "Demo Workspace";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["list"], ["html", { open: "never" }]],
  outputDir: "test-results/e2e",
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      name: "FastAPI",
      command:
        "uv run alembic upgrade head && " +
        "uv run python -m quantitative_sentiment_analysis.auth.seed_user && " +
        `uv run uvicorn quantitative_sentiment_analysis.main:app --host ${apiHost} --port ${apiPort}`,
      url: `${apiURL}/health`,
      reuseExistingServer,
      timeout: 120 * 1000,
      env: {
        UV_PROJECT_ENVIRONMENT:
          process.env.UV_PROJECT_ENVIRONMENT ?? "/tmp/qsa-postgres-auth-venv",
        UV_LINK_MODE: process.env.UV_LINK_MODE ?? "copy",
        DATABASE_URL: requiredDatabaseUrl(),
        AUTH_SECRET: requiredAuthSecret(),
        QSA_SESSION_COOKIE_SECURE: "false",
        QSA_CORS_ALLOWED_ORIGINS: baseURL,
        QSA_SEED_USER_EMAIL: e2eEmail,
        QSA_SEED_USER_PASSWORD: e2ePassword,
        QSA_SEED_WORKSPACE_SLUG: e2eWorkspaceSlug,
        QSA_SEED_WORKSPACE_NAME: e2eWorkspaceName,
      },
    },
    {
      name: "Vite",
      command: `npm --prefix frontend run dev -- --host ${frontendHost} --port ${frontendPort} --strictPort`,
      url: baseURL,
      reuseExistingServer,
      timeout: 120 * 1000,
      env: {
        VITE_API_BASE_URL: "",
        VITE_API_PROXY_TARGET: apiURL,
      },
    },
  ],
});

function requiredDatabaseUrl(): string {
  const databaseUrl =
    process.env.DATABASE_URL ?? process.env.QSA_TEST_DATABASE_URL;
  if (!databaseUrl) {
    throw new Error(
      "DATABASE_URL or QSA_TEST_DATABASE_URL is required to run Playwright E2E.",
    );
  }
  return databaseUrl;
}

function requiredAuthSecret(): string {
  return (
    process.env.AUTH_SECRET ??
    "local-e2e-auth-secret-with-at-least-32-characters"
  );
}
