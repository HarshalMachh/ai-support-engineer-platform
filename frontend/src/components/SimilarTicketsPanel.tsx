import { Link } from "react-router-dom";
import type { SimilarTicket } from "../types";
import { formatPercent } from "../utils/format";

export function SimilarTicketsPanel({ tickets }: { tickets: SimilarTicket[] }) {
  return (
    <section className="card">
      <div className="card-header">
        <h3 className="card-title">Similar resolved tickets</h3>
        <span className="text-xs text-slate-500">{tickets.length} found</span>
      </div>
      {tickets.length === 0 ? (
        <p className="px-4 py-3 text-sm text-slate-500">No similar resolved tickets yet.</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {tickets.map((ticket) => (
            <li key={ticket.ticket_id} className="px-4 py-2.5 text-sm">
              <div className="flex items-center justify-between gap-2">
                <Link to={`/agent/tickets/${ticket.ticket_id}`} className="font-medium text-brand-700 hover:underline">
                  <span className="font-mono text-xs text-slate-400">#{ticket.ticket_id}</span> {ticket.subject}
                </Link>
                <span className="font-mono text-xs text-slate-500">{formatPercent(ticket.similarity)}</span>
              </div>
              <p className="mt-1 text-slate-600">{ticket.resolution_summary}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
