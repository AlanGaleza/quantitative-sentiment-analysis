import { BacktestQualityPage } from "./features/backtestQuality/BacktestQualityPage";

interface QualityRoute {
  workspaceId: string;
  runId: string;
}

export function parseQualityRoute(pathname: string): QualityRoute | null {
  const match = /^\/workspaces\/([^/]+)\/backtests\/([^/]+)\/quality\/?$/.exec(
    pathname,
  );

  if (!match) {
    return null;
  }

  return {
    workspaceId: decodeURIComponent(match[1]),
    runId: decodeURIComponent(match[2]),
  };
}

export default function App() {
  const route = parseQualityRoute(window.location.pathname);

  if (!route) {
    return (
      <main className="quality-page">
        <section className="error-state" role="alert">
          Open a run-scoped BACKTEST quality path:
          /workspaces/:workspaceId/backtests/:runId/quality
        </section>
      </main>
    );
  }

  return (
    <BacktestQualityPage
      workspaceId={route.workspaceId}
      runId={route.runId}
    />
  );
}
