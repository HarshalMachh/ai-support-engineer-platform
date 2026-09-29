import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ticketsApi } from "../api/tickets";
import { NewTicketPage } from "../pages/customer/NewTicketPage";
import { makeTicket, renderWithProviders } from "../test/utils";

function renderPage() {
  return renderWithProviders(<NewTicketPage />, {
    route: "/customer/tickets/new",
    path: "/customer/tickets/new",
    extraRoutes: <Route path="/customer/tickets/:id" element={<p>Ticket created page</p>} />,
  });
}

describe("NewTicketPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("validates required fields before submitting", async () => {
    const create = vi.spyOn(ticketsApi, "create");
    renderPage();
    await userEvent.type(screen.getByLabelText("Subject"), "Hey");
    await userEvent.click(screen.getByRole("button", { name: "Submit ticket" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Subject must be at least 5 characters");
    expect(create).not.toHaveBeenCalled();
  });

  it("creates the ticket and navigates to it", async () => {
    const create = vi.spyOn(ticketsApi, "create").mockResolvedValue({
      ...makeTicket({ id: 99 }),
      description: "d",
      resolution_summary: null,
      ai_error: null,
      messages: [],
    });
    renderPage();

    await userEvent.type(screen.getByLabelText("Subject"), "Webhooks not arriving");
    await userEvent.selectOptions(screen.getByLabelText("Environment"), "staging");
    await userEvent.type(screen.getByLabelText("Description"), "No webhook events for two days on staging.");
    await userEvent.click(screen.getByRole("button", { name: "Submit ticket" }));

    expect(create).toHaveBeenCalledWith({
      subject: "Webhooks not arriving",
      description: "No webhook events for two days on staging.",
      environment: "staging",
    });
    expect(await screen.findByText("Ticket created page")).toBeInTheDocument();
  });

  it("shows an error when the API fails", async () => {
    vi.spyOn(ticketsApi, "create").mockRejectedValue(new Error("Network down"));
    renderPage();
    await userEvent.type(screen.getByLabelText("Subject"), "Something broke");
    await userEvent.type(screen.getByLabelText("Description"), "A long enough description.");
    await userEvent.click(screen.getByRole("button", { name: "Submit ticket" }));

    expect(await screen.findByText("Could not create ticket")).toBeInTheDocument();
    expect(screen.getByText("Network down")).toBeInTheDocument();
  });
});
