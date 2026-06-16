import { useEffect, useState, type ReactNode } from "react";

import { LoginPage } from "./features/auth/LoginPage";
import {
  fetchCurrentSession,
  logoutSession,
} from "./features/auth/api";
import type { AuthSessionResponse } from "./features/auth/types";
import { BacktestConfigPage } from "./features/backtestConfigs/BacktestConfigPage";
import { BacktestQualityPage } from "./features/backtestQuality/BacktestQualityPage";
import { BacktestRunHistoryPage } from "./features/backtestRuns/BacktestRunHistoryPage";
import { BacktestShellPage } from "./features/backtestShell/BacktestShellPage";

interface LoginRoute {
  kind: "login";
}

interface ConfigRoute {
  kind: "configs";
  workspaceId: string;
}

interface ShellRoute {
  kind: "shell";
  workspaceId: string;
}

interface HistoryRoute {
  kind: "history";
  workspaceId: string;
}

interface QualityRoute {
  kind: "quality";
  workspaceId: string;
  runId: string;
}

type AppRoute = LoginRoute | ConfigRoute | ShellRoute | HistoryRoute | QualityRoute;

type AuthState =
  | { status: "loading" }
  | { status: "authenticated"; session: AuthSessionResponse }
  | { status: "unauthenticated" };

type LoadCurrentSession = () => Promise<AuthSessionResponse>;
type Logout = () => Promise<void>;

interface AppProps {
  loadCurrentSession?: LoadCurrentSession;
  logout?: Logout;
}

export function parseLoginRoute(pathname: string): LoginRoute | null {
  return /^\/login\/?$/.test(pathname) ? { kind: "login" } : null;
}

export function parseConfigRoute(pathname: string): ConfigRoute | null {
  const match = /^\/workspaces\/([^/]+)\/backtest-configs\/?$/.exec(pathname);

  if (!match) {
    return null;
  }

  try {
    return {
      kind: "configs",
      workspaceId: decodeURIComponent(match[1]),
    };
  } catch {
    return null;
  }
}

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

export function parseHistoryRoute(pathname: string): HistoryRoute | null {
  const match = /^\/workspaces\/([^/]+)\/backtests\/?$/.exec(pathname);

  if (!match) {
    return null;
  }

  try {
    return {
      kind: "history",
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
  return (
    parseLoginRoute(pathname) ??
    parseConfigRoute(pathname) ??
    parseHistoryRoute(pathname) ??
    parseShellRoute(pathname) ??
    parseQualityRoute(pathname)
  );
}

export function defaultWorkspacePath(session: AuthSessionResponse): string {
  const workspaceSlug =
    session.default_workspace_slug ?? session.workspaces[0]?.slug ?? null;

  if (!workspaceSlug) {
    return "/login";
  }

  return `/workspaces/${encodeURIComponent(workspaceSlug)}/backtests`;
}

export default function App({
  loadCurrentSession = fetchCurrentSession,
  logout = logoutSession,
}: AppProps = {}) {
  const [pathname, setPathname] = useState(window.location.pathname);
  const [authState, setAuthState] = useState<AuthState>({ status: "loading" });
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const route = parseAppRoute(pathname);
  const routeKind = route?.kind;

  useEffect(() => {
    let isCurrent = true;

    loadCurrentSession()
      .then((session) => {
        if (isCurrent) {
          setAuthState({ status: "authenticated", session });
        }
      })
      .catch(() => {
        if (isCurrent) {
          setAuthState({ status: "unauthenticated" });
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [loadCurrentSession]);

  useEffect(() => {
    function handlePopState() {
      setPathname(window.location.pathname);
    }

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    if (authState.status !== "authenticated" || routeKind !== "login") {
      return;
    }

    window.history.replaceState({}, "", defaultWorkspacePath(authState.session));
    setPathname(window.location.pathname);
  }, [authState, routeKind]);

  function navigate(path: string) {
    window.history.pushState({}, "", path);
    setPathname(window.location.pathname);
  }

  function handleLoginSuccess(session: AuthSessionResponse) {
    setAuthState({ status: "authenticated", session });
    navigate(defaultWorkspacePath(session));
  }

  async function handleLogout() {
    setLogoutError(null);
    try {
      await logout();
    } catch (error) {
      setLogoutError(error instanceof Error ? error.message : "Logout failed.");
    }
    setAuthState({ status: "unauthenticated" });
    navigate("/login");
  }

  if (authState.status === "loading") {
    return (
      <main className="quality-page">
        <p role="status" className="loading-state">
          Loading workspace session...
        </p>
      </main>
    );
  }

  if (route?.kind === "login") {
    if (authState.status === "authenticated") {
      return (
        <main className="quality-page">
          <p role="status" className="loading-state">
            Opening workspace...
          </p>
        </main>
      );
    }
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  if (authState.status === "unauthenticated") {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <AuthenticatedFrame
      session={authState.session}
      logoutError={logoutError}
      onLogout={() => void handleLogout()}
    >
      {route ? (
        <ProtectedRoute route={route} />
      ) : (
        <main className="quality-page">
          <section className="error-state" role="alert">
            Open a workspace BACKTEST path:
            /workspaces/:workspaceId/backtests,
            /workspaces/:workspaceId/backtest-configs,
            /workspaces/:workspaceId/backtests/new, or
            /workspaces/:workspaceId/backtests/:runId/quality
          </section>
        </main>
      )}
    </AuthenticatedFrame>
  );
}

function ProtectedRoute({ route }: { route: Exclude<AppRoute, LoginRoute> }) {
  if (route.kind === "configs") {
    return <BacktestConfigPage workspaceId={route.workspaceId} />;
  }

  if (route.kind === "shell") {
    return <BacktestShellPage workspaceId={route.workspaceId} />;
  }

  if (route.kind === "history") {
    return <BacktestRunHistoryPage workspaceId={route.workspaceId} />;
  }

  return (
    <BacktestQualityPage
      workspaceId={route.workspaceId}
      runId={route.runId}
    />
  );
}

function AuthenticatedFrame({
  session,
  logoutError,
  onLogout,
  children,
}: {
  session: AuthSessionResponse;
  logoutError: string | null;
  onLogout: () => void;
  children: ReactNode;
}) {
  const defaultWorkspace = session.default_workspace_slug ?? session.workspaces[0]?.slug;
  return (
    <>
      <nav className="app-nav" aria-label="Workspace navigation">
        <div>
          <strong>{session.user.email}</strong>
          {defaultWorkspace ? <span>{defaultWorkspace}</span> : null}
        </div>
        <div className="app-nav-actions">
          {defaultWorkspace ? (
            <>
              <a href={`/workspaces/${encodeURIComponent(defaultWorkspace)}/backtests`}>
                Run history
              </a>
              <a href={`/workspaces/${encodeURIComponent(defaultWorkspace)}/backtest-configs`}>
                Saved configs
              </a>
              <a href={`/workspaces/${encodeURIComponent(defaultWorkspace)}/backtests/new`}>
                New BACKTEST
              </a>
            </>
          ) : null}
          <button className="secondary-button" type="button" onClick={onLogout}>
            Log out
          </button>
        </div>
      </nav>
      {logoutError ? (
        <div className="quality-page nav-alert">
          <div role="alert" className="inline-alert">
            {logoutError}
          </div>
        </div>
      ) : null}
      {children}
    </>
  );
}
