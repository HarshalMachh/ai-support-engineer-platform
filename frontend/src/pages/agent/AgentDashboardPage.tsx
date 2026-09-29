import { Link } from "react-router-dom";
import { AnalyticsCard } from "../../components/AnalyticsCard";
import { ErrorMessage } from "../../components/ErrorMessage";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { TicketTable } from "../../components/TicketTable";
import { useAIAnalytics, useTicketAnalytics } from "../../hooks/useAnalytics";
import { useTickets } from "../../hooks/useTickets";
import { formatPercent } from "../../utils/format";

export function AgentDashboardPage() {
  const ticketStats = useTicketAnalytics();
  const aiStats = useAIAnalytics();
  const mine = useTickets({ assigned_agent: "me", page: 1, page_size: 5 });
  const unassigned = useTickets({ assigned_agent: "unassigned", status: "OPEN", page: 1, page_size: 5 });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="page-title">Agent dashboard</h1>
        <Link to="/agent/tickets" className="btn-primary">Open ticket queue</Link>
      </div>

      {ticketStats.isError && <ErrorMessage error={ticketStats.error} title="Could not load metrics" />}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <AnalyticsCard label="Open" value={ticketStats.data?.open_tickets ?? "—"} />
        <AnalyticsCard label="In progress" value={ticketStats.data?.in_progress_tickets ?? "—"} />
        <AnalyticsCard label="Critical (active)" value={ticketStats.data?.critical_tickets ?? "—"} tone="danger" />
        <AnalyticsCard label="Unassigned" value={ticketStats.data?.unassigned_tickets ?? "—"} tone="warning" />
        <AnalyticsCard label="Resolved" value={ticketStats.data?.resolved_tickets ?? "—"} tone="success" />
        <AnalyticsCard
          label="AI acceptance"
          value={formatPercent(aiStats.data?.acceptance_rate)}
          hint="approved + edited / reviewed"
        />
      </div>

      <section className="card">
        <div className="card-header">
          <h2 className="card-title">Assigned to me</h2>
          <Link to="/agent/tickets" className="text-xs text-brand-700 hover:underline">View all</Link>
        </div>
        {mine.isLoading ? (
          <LoadingSpinner className="p-4" />
        ) : (
          <TicketTable
            tickets={mine.data?.items ?? []}
            linkTo={(t) => `/agent/tickets/${t.id}`}
            emptyMessage="Nothing assigned to you right now."
          />
        )}
      </section>

      <section className="card">
        <div className="card-header">
          <h2 className="card-title">Unassigned open tickets</h2>
        </div>
        {unassigned.isLoading ? (
          <LoadingSpinner className="p-4" />
        ) : (
          <TicketTable
            tickets={unassigned.data?.items ?? []}
            linkTo={(t) => `/agent/tickets/${t.id}`}
            emptyMessage="All open tickets are assigned. 🎉"
          />
        )}
      </section>
    </div>
  );
}
