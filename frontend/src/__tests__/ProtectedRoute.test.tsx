import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { ProtectedRoute } from "../components/ProtectedRoute";
import { RoleProtectedRoute } from "../components/RoleProtectedRoute";
import { AuthContext, type AuthContextValue } from "../context/AuthContext";
import { makeAuth, makeUser } from "../test/utils";

function renderAt(route: string, auth: AuthContextValue) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <AuthContext.Provider value={auth}>
        <MemoryRouter initialEntries={[route]}>
          <Routes>
            <Route path="/login" element={<p>Login page</p>} />
            <Route path="/customer/dashboard" element={<p>Customer home</p>} />
            <Route element={<ProtectedRoute />}>
              <Route element={<RoleProtectedRoute allowedRoles={["AGENT", "ADMIN"]} />}>
                <Route path="/agent/tickets" element={<p>Agent queue</p>} />
              </Route>
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}

describe("ProtectedRoute / RoleProtectedRoute", () => {
  it("redirects anonymous users to login", () => {
    renderAt("/agent/tickets", makeAuth({ user: null }));
    expect(screen.getByText("Login page")).toBeInTheDocument();
  });

  it("shows a loading state while the session is being checked", () => {
    renderAt("/agent/tickets", makeAuth({ user: null, isLoading: true }));
    expect(screen.getByRole("status")).toHaveTextContent("Checking session");
  });

  it("renders the page for an allowed role", () => {
    renderAt("/agent/tickets", makeAuth({ user: makeUser({ role: "AGENT" }) }));
    expect(screen.getByText("Agent queue")).toBeInTheDocument();
  });

  it("redirects users without the required role to their home page", () => {
    renderAt("/agent/tickets", makeAuth({ user: makeUser({ role: "CUSTOMER" }) }));
    expect(screen.getByText("Customer home")).toBeInTheDocument();
    expect(screen.queryByText("Agent queue")).not.toBeInTheDocument();
  });
});
