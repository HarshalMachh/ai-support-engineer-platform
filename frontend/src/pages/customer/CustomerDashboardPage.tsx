import { Link } from "react-router-dom";
import { AnalyticsCard } from "../../components/AnalyticsCard";
import { ErrorMessage } from "../../components/ErrorMessage";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { TicketCard } from "../../components/TicketCard";
import { useAuth } from "../../hooks/useAuth";
import { useTickets } from "../../hooks/useTickets";

export function CustomerDashboardPage() {
  const { user } = useAuth();
  const recent = useTickets({ page: 1, page_size: 5 });
  const open = useTickets({ status: "OPEN", page: 1, page_size: 1 });
  const waiting = useTickets({ status: "WAITING_FOR_CUSTOMER", page: 1, page_size: 1 });
  const resolved = useTickets({ status: "RESOLVED", page: 1, page_size: 1 });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Welcome back, {user?.name.split(" ")[0]}</h1>
          <p className="text-sm text-slate-500">Track your support requests and replies from our team.</p>
        </div>
        <Link to="/customer/tickets/new" className="btn-primary">
          New ticket
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <AnalyticsCard label="All tickets" value={recent.data?.total ?? "—"} />
        <AnalyticsCard label="Open" value={open.data?.total ?? "—"} />
        <AnalyticsCard label="Awaiting your reply" value={waiting.data?.total ?? "—"} tone="warning" />
        <AnalyticsCard label="Resolved" value={resolved.data?.total ?? "—"} tone="success" />
      </div>

      <section className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700">Recent tickets</h2>
          <Link to="/customer/tickets" className="text-sm text-brand-700 hover:underline">
            View all
          </Link>
        </div>
        {recent.isLoading && <LoadingSpinner />}
        {recent.isError && <ErrorMessage error={recent.error} onRetry={() => recent.refetch()} />}
        {recent.data?.items.length === 0 && (
          <div className="card px-4 py-8 text-center text-sm text-slate-500">
            You have no tickets yet.{" "}
            <Link to="/customer/tickets/new" className="text-brand-700 hover:underline">
              Create your first ticket
            </Link>
          </div>
        )}
        <div className="grid gap-2">
          {recent.data?.items.map((ticket) => (
            <TicketCard key={ticket.id} ticket={ticket} to={`/customer/tickets/${ticket.id}`} />
          ))}
        </div>
      </section>
    </div>
  );
}
