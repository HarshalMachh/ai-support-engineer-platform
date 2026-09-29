import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";
import { AuthContext, type AuthContextValue } from "../context/AuthContext";
import type { AIResponse, TicketSummary, User } from "../types";

export function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: 1,
    name: "Carol Customer",
    email: "carol@customer.dev",
    role: "CUSTOMER",
    is_active: true,
    created_at: "2026-09-01T10:00:00Z",
    updated_at: "2026-09-01T10:00:00Z",
    ...overrides,
  };
}

export function makeAuth(overrides: Partial<AuthContextValue> = {}): AuthContextValue {
  const user = overrides.user === undefined ? makeUser() : overrides.user;
  return {
    user,
    isLoading: false,
    isAuthenticated: Boolean(user),
    sessionExpired: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    ...overrides,
  };
}

export function makeTicket(overrides: Partial<TicketSummary> = {}): TicketSummary {
  return {
    id: 42,
    subject: "API returns 401 with new key",
    environment: "production",
    category: "API",
    priority: "HIGH",
    status: "OPEN",
    ai_confidence: 0.91,
    ai_analysis_status: "COMPLETED",
    customer: { id: 1, name: "Carol Customer", email: "carol@customer.dev", role: "CUSTOMER" },
    assigned_agent: null,
    created_at: "2026-09-27T10:00:00Z",
    updated_at: "2026-09-27T10:00:00Z",
    resolved_at: null,
    ...overrides,
  };
}

export function makeAIResponse(overrides: Partial<AIResponse> = {}): AIResponse {
  return {
    id: 7,
    ticket_id: 42,
    generated_response: "Please confirm your key starts with ak_live_.",
    edited_response: null,
    reasoning_summary: "Knowledge base explains key prefixes.",
    confidence_score: 0.82,
    status: "PENDING",
    approver: null,
    category: "API",
    classification_confidence: 0.91,
    priority: "HIGH",
    priority_reason: "Production API failing",
    requires_more_information: false,
    requested_information: [],
    source_references: ["API Keys"],
    knowledge_results: [],
    similar_tickets: [],
    warnings: [],
    model_name: "qwen2.5:7b",
    rejection_reason: null,
    created_at: "2026-09-27T10:00:00Z",
    updated_at: "2026-09-27T10:00:00Z",
    ...overrides,
  };
}

interface RenderOptions {
  auth?: AuthContextValue;
  route?: string;
  path?: string;
  extraRoutes?: ReactNode;
}

/** Render with React Query, an in-memory router and a controllable auth context. */
export function renderWithProviders(
  ui: ReactElement,
  { auth = makeAuth(), route = "/", path = "*", extraRoutes }: RenderOptions = {},
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider value={auth}>
        <MemoryRouter initialEntries={[route]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Routes>
            <Route path={path} element={ui} />
            {extraRoutes}
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}
