import type { TicketPriority } from "../types";
import { humanize } from "../utils/format";

const PRIORITY_STYLES: Record<TicketPriority, string> = {
  LOW: "bg-slate-50 text-slate-600 ring-slate-500/20",
  MEDIUM: "bg-blue-50 text-blue-700 ring-blue-600/20",
  HIGH: "bg-orange-50 text-orange-700 ring-orange-600/20",
  CRITICAL: "bg-rose-50 text-rose-700 ring-rose-600/30",
};

export function PriorityBadge({ priority }: { priority: TicketPriority | null }) {
  if (!priority) {
    return <span className="badge bg-white text-slate-400 ring-slate-300">Untriaged</span>;
  }
  return <span className={`badge ${PRIORITY_STYLES[priority]}`}>{humanize(priority)}</span>;
}
