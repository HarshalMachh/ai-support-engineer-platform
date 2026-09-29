import {
  TICKET_CATEGORIES,
  TICKET_PRIORITIES,
  TICKET_STATUSES,
  type TicketCategory,
  type TicketFilters as Filters,
  type TicketPriority,
  type TicketStatus,
} from "../types";
import { humanize } from "../utils/format";

interface TicketFiltersProps {
  filters: Filters;
  onChange: (filters: Filters) => void;
  showAssignee?: boolean;
}

export function TicketFilters({ filters, onChange, showAssignee = true }: TicketFiltersProps) {
  const update = (patch: Partial<Filters>) => onChange({ ...filters, ...patch, page: 1 });

  return (
    <div className="flex flex-wrap gap-2">
      <select
        className="input w-auto"
        aria-label="Filter by status"
        value={filters.status ?? ""}
        onChange={(e) => update({ status: e.target.value as TicketStatus | "" })}
      >
        <option value="">All statuses</option>
        {TICKET_STATUSES.map((status) => (
          <option key={status} value={status}>
            {humanize(status)}
          </option>
        ))}
      </select>
      <select
        className="input w-auto"
        aria-label="Filter by priority"
        value={filters.priority ?? ""}
        onChange={(e) => update({ priority: e.target.value as TicketPriority | "" })}
      >
        <option value="">All priorities</option>
        {TICKET_PRIORITIES.map((priority) => (
          <option key={priority} value={priority}>
            {humanize(priority)}
          </option>
        ))}
      </select>
      <select
        className="input w-auto"
        aria-label="Filter by category"
        value={filters.category ?? ""}
        onChange={(e) => update({ category: e.target.value as TicketCategory | "" })}
      >
        <option value="">All categories</option>
        {TICKET_CATEGORIES.map((category) => (
          <option key={category} value={category}>
            {humanize(category)}
          </option>
        ))}
      </select>
      {showAssignee && (
        <select
          className="input w-auto"
          aria-label="Filter by assignee"
          value={filters.assigned_agent ?? ""}
          onChange={(e) => update({ assigned_agent: e.target.value })}
        >
          <option value="">Anyone</option>
          <option value="me">Assigned to me</option>
          <option value="unassigned">Unassigned</option>
        </select>
      )}
    </div>
  );
}
