import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AuthApiError } from "./api";
import { LoginPage } from "./LoginPage";
import type { AuthSessionResponse } from "./types";

describe("LoginPage", () => {
  it("submits credentials and returns the authenticated session", async () => {
    const session = authSession();
    const login = vi.fn().mockResolvedValue(session);
    const onLoginSuccess = vi.fn();

    render(<LoginPage login={login} onLoginSuccess={onLoginSuccess} />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "trader@example.test" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "secret-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(onLoginSuccess).toHaveBeenCalledWith(session));
    expect(login).toHaveBeenCalledWith("trader@example.test", "secret-password");
    expect(screen.getByLabelText("Password")).toHaveValue("");
  });

  it("shows a generic alert for invalid credentials", async () => {
    const login = vi
      .fn()
      .mockRejectedValue(new AuthApiError(401, "invalid credentials"));

    render(<LoginPage login={login} onLoginSuccess={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "trader@example.test" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "wrong-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Email or password is incorrect.",
    );
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
