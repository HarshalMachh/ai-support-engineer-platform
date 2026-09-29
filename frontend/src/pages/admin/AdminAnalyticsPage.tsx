import { AnalyticsCard } from "../../components/AnalyticsCard";
import { BarList } from "../../components/BarList";
import { ErrorMessage } from "../../components/ErrorMessage";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { useAIAnalytics, useTicketAnalytics } from "../../hooks/useAnalytics";
import { formatPercent } from "../../utils/format";

export function AdminAnalyticsPage() {
  const tickets = useTicketAnalytics();
  const ai = useAIAnalytics();

  if (tickets.isLoading || ai.isLoading) return <LoadingSpinner />;
  if (tickets.isError || ai.isError || !tickets.data || !ai.data) {
    return <ErrorMessage error={tickets.error ?? ai.error} title="Could not load analytics" />;
  }

  const t = tickets.data;
  const a = ai.data;
  const avgHours = t.average_resolution_time_hours;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Analytics</h1>
        <p className="text-sm text-slate-500">All metrics are computed live from the database.</p>
      </div>

      <section className="space-y-2">
        <h2 className="text-sm font-semibold text-slate-700">Tickets</h2>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
          <AnalyticsCard label="Total" value={t.total_tickets} />
          <AnalyticsCard label="Open" value={t.open_tickets} />
          <AnalyticsCard label="Critical (active)" value={t.critical_tickets} tone="danger" />
          <AnalyticsCard label="Resolved" value={t.resolved_tickets} tone="success" />
          <AnalyticsCard label="Closed" value={t.closed_tickets} />
          <AnalyticsCard
            label="Avg. resolution"
            value={avgHours === null ? "—" : avgHours < 48 ? `${avgHours.toFixed(1)} h` : `${(avgHours / 24).toFixed(1)} d`}
          />
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          <BarList title="By status" data={t.tickets_by_status} />
          <BarList title="By priority" data={t.tickets_by_priority} />
          <BarList title="By category" data={t.tickets_by_category} />
        </div>
      </section>

      <section className="space-y-2">
        <h2 className="text-sm font-semibold text-slate-700">AI responses</h2>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-8">
          <AnalyticsCard label="Drafts generated" value={a.total_responses} />
          <AnalyticsCard label="Pending review" value={a.pending_count} tone="warning" />
          <AnalyticsCard label="Approved" value={a.approved_count} tone="success" />
          <AnalyticsCard label="Edited" value={a.edited_count} />
          <AnalyticsCard label="Rejected" value={a.rejected_count} tone="danger" />
          <AnalyticsCard label="Approval rate" value={formatPercent(a.approval_rate)} hint="approved as-is / reviewed" />
          <AnalyticsCard label="Acceptance rate" value={formatPercent(a.acceptance_rate)} hint="approved + edited" />
          <AnalyticsCard
            label="Avg. rating"
            value={a.average_feedback_rating?.toFixed(1) ?? "—"}
            hint={`${a.feedback_count} ratings`}
          />
        </div>
      </section>
    </div>
  );
}
