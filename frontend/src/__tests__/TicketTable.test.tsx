import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { TicketTable } from "../components/TicketTable";
import { makeTicket, renderWithProviders } from "../test/utils";

describe("TicketTable", () => {
  it("renders ticket rows with status, priority and category", () => {
    const tickets = [
      makeTicket(),
      makeTicket({
        id: 43,
        subject: "Charged twice",
        status: "WAITING_FOR_CUSTOMER",
        priority: null,
        category: null,
        ai_confidence: null,
        assigned_agent: { id: 2, name: "Alice Agent", email: "alice@supportdesk.dev", role: "AGENT" },
      }),
    ];
    renderWithProviders(<TicketTable tickets={tickets} linkTo={(t) => `/agent/tickets/${t.id}`} />);

    expect(screen.getAllByRole("row")).toHaveLength(3);
    expect(screen.getByText("API returns 401 with new key")).toBeInTheDocument();
    expect(screen.getByText("Charged twice")).toBeInTheDocument();
    expect(screen.getByText("Waiting For Customer")).toBeInTheDocument();
    expect(screen.getByText("High")).toBeInTheDocument();
    expect(screen.getByText("Untriaged")).toBeInTheDocument();
    expect(screen.getByText("Alice Agent")).toBeInTheDocument();
    expect(screen.getByText("91%")).toBeInTheDocument();
  });

  it("shows the empty message when there are no tickets", () => {
    renderWithProviders(<TicketTable tickets={[]} linkTo={() => "/"} emptyMessage="Nothing here" />);
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
  });

  it("navigates to the ticket when a row is clicked", async () => {
    renderWithProviders(<TicketTable tickets={[makeTicket()]} linkTo={(t) => `/agent/tickets/${t.id}`} />, {
      route: "/agent/tickets",
      path: "/agent/tickets",
      extraRoutes: <Route path="/agent/tickets/:id" element={<p>Ticket detail page</p>} />,
    });
    await userEvent.click(screen.getByText("API returns 401 with new key"));
    expect(await screen.findByText("Ticket detail page")).toBeInTheDocument();
  });
});
