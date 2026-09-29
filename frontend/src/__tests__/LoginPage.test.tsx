import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { LoginPage } from "../pages/LoginPage";
import { makeAuth, makeUser, renderWithProviders } from "../test/utils";

describe("LoginPage", () => {
  it("submits credentials and redirects to the role home page", async () => {
    const login = vi.fn().mockResolvedValue(makeUser({ role: "AGENT" }));
    renderWithProviders(<LoginPage />, {
      auth: makeAuth({ user: null, login }),
      route: "/login",
      path: "/login",
      extraRoutes: <Route path="/agent/dashboard" element={<p>Agent home</p>} />,
    });

    await userEvent.type(screen.getByLabelText("Email"), "alice@supportdesk.dev");
    await userEvent.type(screen.getByLabelText("Password"), "Agent123!");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(login).toHaveBeenCalledWith({ email: "alice@supportdesk.dev", password: "Agent123!" });
    expect(await screen.findByText("Agent home")).toBeInTheDocument();
  });

  it("shows the server error on invalid login", async () => {
    const error = Object.assign(new Error("Request failed"), {
      isAxiosError: true,
      response: { status: 401, data: { detail: "Invalid email or password" } },
    });
    const login = vi.fn().mockRejectedValue(error);
    renderWithProviders(<LoginPage />, { auth: makeAuth({ user: null, login }), route: "/login", path: "/login" });

    await userEvent.type(screen.getByLabelText("Email"), "ghost@customer.dev");
    await userEvent.type(screen.getByLabelText("Password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Invalid email or password"));
  });

  it("tells the user when their session expired", () => {
    renderWithProviders(<LoginPage />, { auth: makeAuth({ user: null, sessionExpired: true }) });
    expect(screen.getByText(/session expired/i)).toBeInTheDocument();
  });
});
