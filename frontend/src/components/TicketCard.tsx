import { Link } from "react-router-dom";
import type { TicketSummary } from "../types";
import { formatRelative, humanize } from "../utils/format";
import { PriorityBadge } from "./PriorityBadge";
import { TicketStatusBadge } from "./TicketStatusBadge";

interface TicketCardProps {
  ticket: TicketSummary;
  to: string;
}

export function TicketCard({ ticket, to }: TicketCardProps) {
  return (
    <Link to={to} className="card block px-4 py-3 transition hover:border-brand-300 hover:shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-mono text-xs text-slate-400">#{ticket.id}</p>
          <p className="truncate font-medium text-slate-900">{ticket.subject}</p>
          <p className="mt-1 text-xs text-slate-500">
            {humanize(ticket.environment)} · updated {formatRelative(ticket.updated_at)}
          </p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <TicketStatusBadge status={ticket.status} />
          <PriorityBadge priority={ticket.priority} />
        </div>
      </div>
    </Link>
  );
}
