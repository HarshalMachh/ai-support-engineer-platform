import { Link } from "react-router-dom";
import { AnalyticsCard } from "../../components/AnalyticsCard";
import { ErrorMessage } from "../../components/ErrorMessage";
import { useAIAnalytics, useTicketAnalytics } from "../../hooks/useAnalytics";
import { useKnowledgeDocuments } from "../../hooks/useKnowledge";
import { useUsers } from "../../hooks/useUsers";
import { formatPercent } from "../../utils/format";

export function AdminDashboardPage() {
  const tickets = useTicketAnalytics();
  const ai = useAIAnalytics();
  const customers = useUsers({ role: "CUSTOMER", page: 1, page_size: 1 });
  const agents = useUsers({ role: "AGENT", page: 1, page_size: 1 });
  const documents = useKnowledgeDocuments();

  const links = [
    { to: "/admin/users", title: "Users", body: "Browse customers, agents and admins." },
    { to: "/admin/knowledge", title: "Knowledge base", body: "Upload .md / .txt docs used for RAG." },
    { to: "/admin/analytics", title: "Analytics", body: "Ticket and AI acceptance metrics." },
    { to: "/agent/tickets", title: "Ticket queue", body: "Work tickets like an agent." },
  ];

  return (
    <div className="space-y-6">
      <h1 className="page-title">Admin dashboard</h1>
      {(tickets.isError || ai.isError) && <ErrorMessage error={tickets.error ?? ai.error} title="Could not load metrics" />}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <AnalyticsCard label="Total tickets" value={tickets.data?.total_tickets ?? "—"} />
        <AnalyticsCard label="Open" value={tickets.data?.open_tickets ?? "—"} />
        <AnalyticsCard label="Customers" value={customers.data?.total ?? "—"} />
        <AnalyticsCard label="Agents" value={agents.data?.total ?? "—"} />
        <AnalyticsCard label="Documents" value={documents.data?.length ?? "—"} />
        <AnalyticsCard label="AI approval rate" value={formatPercent(ai.data?.approval_rate)} />
      </div>

      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
        {links.map((link) => (
          <Link key={link.to} to={link.to} className="card block p-4 transition hover:border-brand-300 hover:shadow">
            <p className="font-medium text-slate-900">{link.title}</p>
            <p className="mt-1 text-sm text-slate-500">{link.body}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
