import type { TicketStatus } from "../types";
import { humanize } from "../utils/format";

const STATUS_STYLES: Record<TicketStatus, string> = {
  OPEN: "bg-sky-50 text-sky-700 ring-sky-600/20",
  IN_PROGRESS: "bg-violet-50 text-violet-700 ring-violet-600/20",
  WAITING_FOR_CUSTOMER: "bg-amber-50 text-amber-800 ring-amber-600/20",
  RESOLVED: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  CLOSED: "bg-slate-100 text-slate-600 ring-slate-500/20",
};

export function TicketStatusBadge({ status }: { status: TicketStatus }) {
  return <span className={`badge ${STATUS_STYLES[status]}`}>{humanize(status)}</span>;
}
