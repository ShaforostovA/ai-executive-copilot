import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AuthContext } from "../auth/AuthContext";
import { LoginPage } from "./LoginPage";

describe("LoginPage", () => {
  it("submits organization, email and password to server auth", async () => {
    const login = vi.fn().mockResolvedValue(undefined);
    render(
      <AuthContext.Provider value={{ user: null, loading: false, error: null, login, logout: vi.fn(), expireSession: vi.fn() }}>
        <LoginPage />
      </AuthContext.Provider>,
      { wrapper: MemoryRouter },
    );
    await userEvent.type(screen.getByLabelText("Email"), "demo@example.test");
    await userEvent.type(screen.getByLabelText("Пароль"), "synthetic-password");
    await userEvent.click(screen.getByRole("button", { name: "Войти" }));
    expect(login).toHaveBeenCalledWith({
      organization_slug: "demo",
      email: "demo@example.test",
      password: "synthetic-password",
    });
  });
});
