import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ConversationMessage } from "../../components/ConversationMessage";
import { ErrorMessage } from "../../components/ErrorMessage";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { MessageComposer } from "../../components/MessageComposer";
import { Modal } from "../../components/Modal";
import { TicketStatusBadge } from "../../components/TicketStatusBadge";
import { useAddMessage, useTicket, useUpdateTicket } from "../../hooks/useTickets";
import { formatDateTime, humanize } from "../../utils/format";

const REFRESH_MS = 15_000;

export function CustomerTicketDetailPage() {
  const ticketId = Number(useParams().id);
  const ticketQuery = useTicket(ticketId, { refetchInterval: REFRESH_MS });
  const addMessage = useAddMessage(ticketId);
  const updateTicket = useUpdateTicket(ticketId);
  const [confirmClose, setConfirmClose] = useState(false);

  if (ticketQuery.isLoading) return <LoadingSpinner />;
  if (ticketQuery.isError || !ticketQuery.data) {
    return (
      <div className="space-y-3">
        <ErrorMessage error={ticketQuery.error} title="Ticket not available" />
        <Link to="/customer/tickets" className="btn-secondary">Back to my tickets</Link>
      </div>
    );
  }

  const ticket = ticketQuery.data;
  const isClosed = ticket.status === "CLOSED";

  return (
    <div className="space-y-4">
      <Link to="/customer/tickets" className="text-sm text-brand-700 hover:underline">← My tickets</Link>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-mono text-xs text-slate-400">#{ticket.id}</p>
          <h1 className="page-title">{ticket.subject}</h1>
          <p className="text-sm text-slate-500">
            {humanize(ticket.environment)} · opened {formatDateTime(ticket.created_at)}
            {ticket.assigned_agent && ` · handled by ${ticket.assigned_agent.name}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <TicketStatusBadge status={ticket.status} />
          {!isClosed && (
            <button type="button" className="btn-secondary" onClick={() => setConfirmClose(true)}>
              Close ticket
            </button>
          )}
        </div>
      </div>

      {ticket.status === "RESOLVED" && ticket.resolution_summary && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
          <p className="font-medium">Resolved</p>
          <p>{ticket.resolution_summary}</p>
          <p className="mt-1 text-xs">Still having trouble? Reply below to reopen the ticket.</p>
        </div>
      )}

      <section className="space-y-3" aria-label="Conversation">
        {ticket.messages.map((message) => (
          <ConversationMessage key={message.id} message={message} />
        ))}
      </section>

      {isClosed ? (
        <p className="card px-4 py-3 text-sm text-slate-500">This ticket is closed. Open a new ticket if you need more help.</p>
      ) : (
        <div className="card p-4">
          <MessageComposer
            onSend={(message) => addMessage.mutateAsync(message)}
            isSending={addMessage.isPending}
            error={addMessage.error}
          />
        </div>
      )}

      <Modal
        open={confirmClose}
        title="Close this ticket?"
        onClose={() => setConfirmClose(false)}
        footer={
          <>
            <button type="button" className="btn-secondary" onClick={() => setConfirmClose(false)}>Cancel</button>
            <button
              type="button"
              className="btn-danger"
              disabled={updateTicket.isPending}
              onClick={() => updateTicket.mutate({ status: "CLOSED" }, { onSuccess: () => setConfirmClose(false) })}
            >
              Close ticket
            </button>
          </>
        }
      >
        <p className="text-sm text-slate-600">Closed tickets cannot receive new replies.</p>
        {Boolean(updateTicket.error) && <ErrorMessage error={updateTicket.error} />}
      </Modal>
    </div>
  );
}
