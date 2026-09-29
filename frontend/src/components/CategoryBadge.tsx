import type { TicketCategory } from "../types";
import { humanize } from "../utils/format";

export function CategoryBadge({ category }: { category: TicketCategory | null }) {
  if (!category) {
    return <span className="badge bg-white text-slate-400 ring-slate-300">Uncategorized</span>;
  }
  return <span className="badge bg-indigo-50 font-mono text-indigo-700 ring-indigo-600/20">{humanize(category)}</span>;
}
