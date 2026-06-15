import { BacktestQualityPage } from "./features/backtestQuality/BacktestQualityPage";
import { BacktestShellPage } from "./features/backtestShell/BacktestShellPage";

interface ShellRoute {
  kind: "shell";
  workspaceId: string;
}

interface QualityRoute {
  kind: "quality";
  workspaceId: string;
  runId: string;
}

type AppRoute = ShellRoute | QualityRoute;

export function parseShellRoute(pathname: string): ShellRoute | null {
  const match = /^\/workspaces\/([^/]+)\/backtests\/new\/?$/.exec(pathname);

  if (!match) {
    return null;
  }

  try {
    return {
      kind: "shell",
      workspaceId: decodeURIComponent(match[1]),
    };
  } catch {
    return null;
  }
}

export function parseQualityRoute(pathname: string): QualityRoute | null {
  const match = /^\/workspaces\/([^/]+)\/backtests\/([^/]+)\/quality\/?$/.exec(
    pathname,
  );

  if (!match) {
    return null;
  }

  try {
    return {
      kind: "quality",
      workspaceId: decodeURIComponent(match[1]),
      runId: decodeURIComponent(match[2]),
    };
  } catch {
    return null;
  }
}

export function parseAppRoute(pathname: string): AppRoute | null {
  return parseShellRoute(pathname) ?? parseQualityRoute(pathname);
}

export default function App() {
  const route = parseAppRoute(window.location.pathname);

  if (!route) {
    return (
      <main className="quality-page">
        <section className="error-state" role="alert">
          Open a workspace BACKTEST path:
          /workspaces/:workspaceId/backtests/new or
          /workspaces/:workspaceId/backtests/:runId/quality
        </section>
      </main>
    );
  }

  if (route.kind === "shell") {
    return <BacktestShellPage workspaceId={route.workspaceId} />;
  }

  return (
    <BacktestQualityPage
      workspaceId={route.workspaceId}
      runId={route.runId}
    />
  );
}
