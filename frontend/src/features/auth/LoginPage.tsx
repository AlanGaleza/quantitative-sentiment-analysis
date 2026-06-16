import { FormEvent, useState } from "react";

import { loginWithPassword, type AuthApiError } from "./api";
import type { AuthSessionResponse } from "./types";

type Login = (email: string, password: string) => Promise<AuthSessionResponse>;

interface LoginPageProps {
  login?: Login;
  onLoginSuccess: (session: AuthSessionResponse) => void;
}

type SubmitState =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "error"; message: string };

export function LoginPage({
  login = (email, password) => loginWithPassword({ email, password }),
  onLoginSuccess,
}: LoginPageProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitState, setSubmitState] = useState<SubmitState>({ status: "idle" });

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitState({ status: "submitting" });

    try {
      const session = await login(email, password);
      setPassword("");
      setSubmitState({ status: "idle" });
      onLoginSuccess(session);
    } catch (error) {
      setSubmitState({
        status: "error",
        message: loginErrorMessage(error),
      });
    }
  }

  return (
    <main className="quality-page auth-page">
      <section className="auth-panel" aria-labelledby="login-heading">
        <div>
          <p className="eyebrow">BTCUSD BACKTEST</p>
          <h1 id="login-heading">Workspace login</h1>
          <p className="safety-copy">
            Access is limited to seeded workspace users. Session cookies are
            managed by the backend.
          </p>
        </div>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Email
            <input
              autoComplete="email"
              inputMode="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label>
            Password
            <input
              autoComplete="current-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          {submitState.status === "error" ? (
            <div role="alert" className="inline-alert">
              {submitState.message}
            </div>
          ) : null}
          <div className="form-actions">
            <button type="submit" disabled={submitState.status === "submitting"}>
              {submitState.status === "submitting" ? "Signing in..." : "Sign in"}
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}

function loginErrorMessage(error: unknown): string {
  const apiError = error as Partial<AuthApiError>;
  if (apiError.status === 401) {
    return "Email or password is incorrect.";
  }
  if (typeof apiError.detail === "string" && apiError.detail.length > 0) {
    return apiError.detail;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Login failed.";
}
