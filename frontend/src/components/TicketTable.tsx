import { useNavigate } from "react-router-dom";
import type { TicketSummary } from "../types";
import { formatPercent, formatRelative } from "../utils/format";
import { CategoryBadge } from "./CategoryBadge";
import { PriorityBadge } from "./PriorityBadge";
import { TicketStatusBadge } from "./TicketStatusBadge";

interface TicketTableProps {
  tickets: TicketSummary[];
  linkTo: (ticket: TicketSummary) => string;
  showCustomer?: boolean;
  emptyMessage?: string;
}

export function TicketTable({ tickets, linkTo, showCustomer = true, emptyMessage = "No tickets found." }: TicketTableProps) {
  const navigate = useNavigate();

  if (tickets.length === 0) {
    return <p className="px-4 py-10 text-center text-sm text-slate-500">{emptyMessage}</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-4 py-2">Ticket</th>
            {showCustomer && <th className="px-4 py-2">Customer</th>}
            <th className="px-4 py-2">Status</th>
            <th className="px-4 py-2">Priority</th>
            <th className="px-4 py-2">Category</th>
            <th className="px-4 py-2">AI conf.</th>
            <th className="px-4 py-2">Assignee</th>
            <th className="px-4 py-2">Updated</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {tickets.map((ticket) => (
            <tr
              key={ticket.id}
              className="cursor-pointer hover:bg-slate-50"
              onClick={() => navigate(linkTo(ticket))}
              onKeyDown={(event) => event.key === "Enter" && navigate(linkTo(ticket))}
              tabIndex={0}
            >
              <td className="max-w-md px-4 py-2.5">
                <span className="mr-2 font-mono text-xs text-slate-400">#{ticket.id}</span>
                <span className="font-medium text-slate-900">{ticket.subject}</span>
              </td>
              {showCustomer && <td className="whitespace-nowrap px-4 py-2.5 text-slate-600">{ticket.customer.name}</td>}
              <td className="px-4 py-2.5">
                <TicketStatusBadge status={ticket.status} />
              </td>
              <td className="px-4 py-2.5">
                <PriorityBadge priority={ticket.priority} />
              </td>
              <td className="px-4 py-2.5">
                <CategoryBadge category={ticket.category} />
              </td>
              <td className="px-4 py-2.5 font-mono text-xs text-slate-600">
                {ticket.ai_analysis_status === "RUNNING" ? "running…" : formatPercent(ticket.ai_confidence)}
              </td>
              <td className="whitespace-nowrap px-4 py-2.5 text-slate-600">
                {ticket.assigned_agent?.name ?? <span className="text-slate-400">Unassigned</span>}
              </td>
              <td className="whitespace-nowrap px-4 py-2.5 text-slate-500">{formatRelative(ticket.updated_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
