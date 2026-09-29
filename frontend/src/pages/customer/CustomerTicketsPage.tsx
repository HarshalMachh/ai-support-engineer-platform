import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { ErrorMessage } from "../../components/ErrorMessage";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { Pagination } from "../../components/Pagination";
import { TicketFilters } from "../../components/TicketFilters";
import { TicketSearch } from "../../components/TicketSearch";
import { TicketTable } from "../../components/TicketTable";
import { useTickets } from "../../hooks/useTickets";
import type { TicketFilters as Filters } from "../../types";

export function CustomerTicketsPage() {
  const [filters, setFilters] = useState<Filters>({ page: 1, page_size: 20 });
  const tickets = useTickets(filters);
  const onSearch = useCallback((search: string) => setFilters((f) => ({ ...f, search, page: 1 })), []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="page-title">My tickets</h1>
        <Link to="/customer/tickets/new" className="btn-primary">
          New ticket
        </Link>
      </div>
      <div className="flex flex-col gap-2 lg:flex-row">
        <div className="lg:w-80">
          <TicketSearch value={filters.search ?? ""} onChange={onSearch} />
        </div>
        <TicketFilters filters={filters} onChange={setFilters} showAssignee={false} />
      </div>
      <div className="card">
        {tickets.isLoading && <LoadingSpinner className="p-4" />}
        {tickets.isError && (
          <div className="p-4">
            <ErrorMessage error={tickets.error} onRetry={() => tickets.refetch()} />
          </div>
        )}
        {tickets.data && (
          <TicketTable
            tickets={tickets.data.items}
            linkTo={(ticket) => `/customer/tickets/${ticket.id}`}
            showCustomer={false}
            emptyMessage="No tickets match your filters."
          />
        )}
      </div>
      {tickets.data && tickets.data.total > 0 && (
        <Pagination
          page={tickets.data.page}
          pages={tickets.data.pages}
          total={tickets.data.total}
          onPageChange={(page) => setFilters((f) => ({ ...f, page }))}
        />
      )}
    </div>
  );
}
