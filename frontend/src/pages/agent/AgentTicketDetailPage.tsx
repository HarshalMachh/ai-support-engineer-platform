import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AIAnalysisPanel } from "../../components/AIAnalysisPanel";
import { ConversationMessage } from "../../components/ConversationMessage";
import { ErrorMessage } from "../../components/ErrorMessage";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { MessageComposer } from "../../components/MessageComposer";
import { Modal } from "../../components/Modal";
import { TicketStatusBadge } from "../../components/TicketStatusBadge";
import { useAuth } from "../../hooks/useAuth";
import { useAddMessage, useAssignTicket, useResolveTicket, useTicket, useUpdateTicket } from "../../hooks/useTickets";
import { useAgents } from "../../hooks/useUsers";
import {
  TICKET_CATEGORIES,
  TICKET_PRIORITIES,
  TICKET_STATUSES,
  type TicketCategory,
  type TicketPriority,
  type TicketStatus,
} from "../../types";
import { formatDateTime, humanize } from "../../utils/format";

export function AgentTicketDetailPage() {
  const ticketId = Number(useParams().id);
  const { user } = useAuth();
  const ticketQuery = useTicket(ticketId);
  const agents = useAgents();
  const updateTicket = useUpdateTicket(ticketId);
  const assignTicket = useAssignTicket(ticketId);
  const resolveTicket = useResolveTicket(ticketId);
  const addMessage = useAddMessage(ticketId);
  const [resolveOpen, setResolveOpen] = useState(false);
  const [resolution, setResolution] = useState("");

  if (ticketQuery.isLoading) return <LoadingSpinner />;
  if (ticketQuery.isError || !ticketQuery.data) {
    return (
      <div className="space-y-3">
        <ErrorMessage error={ticketQuery.error} title="Ticket not available" />
        <Link to="/agent/tickets" className="btn-secondary">Back to queue</Link>
      </div>
    );
  }

  const ticket = ticketQuery.data;
  const isFinal = ticket.status === "RESOLVED" || ticket.status === "CLOSED";
  const mutationError = updateTicket.error ?? assignTicket.error;
  const isAdmin = user?.role === "ADMIN";

  return (
    <div className="space-y-4">
      <Link to="/agent/tickets" className="text-sm text-brand-700 hover:underline">← Ticket queue</Link>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-mono text-xs text-slate-400">#{ticket.id}</p>
          <h1 className="page-title">{ticket.subject}</h1>
          <p className="text-sm text-slate-500">
            {ticket.customer.name} ({ticket.customer.email}) · {humanize(ticket.environment)} · opened{" "}
            {formatDateTime(ticket.created_at)}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <TicketStatusBadge status={ticket.status} />
          {ticket.assigned_agent?.id !== user?.id && (
            <button
              type="button"
              className="btn-secondary"
              disabled={assignTicket.isPending}
              onClick={() => assignTicket.mutate(undefined)}
            >
              Assign to me
            </button>
          )}
          {!isFinal && (
            <button type="button" className="btn-primary" onClick={() => setResolveOpen(true)}>
              Resolve
            </button>
          )}
        </div>
      </div>

      {Boolean(mutationError) && <ErrorMessage error={mutationError} title="Update failed" />}

      <section className="card grid grid-cols-2 gap-3 px-4 py-3 md:grid-cols-4" aria-label="Ticket properties">
        <label className="text-xs text-slate-500">
          Status
          <select
            className="input mt-1"
            value={ticket.status}
            onChange={(e) => {
              const status = e.target.value as TicketStatus;
              if (status === "RESOLVED") setResolveOpen(true);
              else updateTicket.mutate({ status });
            }}
          >
            {TICKET_STATUSES.map((status) => (
              <option key={status} value={status}>{humanize(status)}</option>
            ))}
          </select>
        </label>
        <label className="text-xs text-slate-500">
          Priority
          <select
            className="input mt-1"
            value={ticket.priority ?? ""}
            onChange={(e) => updateTicket.mutate({ priority: e.target.value as TicketPriority })}
          >
            {!ticket.priority && <option value="">Untriaged</option>}
            {TICKET_PRIORITIES.map((priority) => (
              <option key={priority} value={priority}>{humanize(priority)}</option>
            ))}
          </select>
        </label>
        <label className="text-xs text-slate-500">
          Category
          <select
            className="input mt-1"
            value={ticket.category ?? ""}
            onChange={(e) => updateTicket.mutate({ category: e.target.value as TicketCategory })}
          >
            {!ticket.category && <option value="">Uncategorized</option>}
            {TICKET_CATEGORIES.map((category) => (
              <option key={category} value={category}>{humanize(category)}</option>
            ))}
          </select>
        </label>
        <label className="text-xs text-slate-500">
          Assignee
          <select
            className="input mt-1"
            value={ticket.assigned_agent?.id ?? ""}
            disabled={!isAdmin}
            title={isAdmin ? undefined : "Only admins can assign to other agents"}
            onChange={(e) =>
              updateTicket.mutate({ assigned_agent_id: e.target.value ? Number(e.target.value) : null })
            }
          >
            <option value="">Unassigned</option>
            {agents.data?.map((agent) => (
              <option key={agent.id} value={agent.id}>{agent.name}</option>
            ))}
          </select>
        </label>
      </section>

      <div className="grid gap-4 xl:grid-cols-5">
        <div className="space-y-3 xl:col-span-3">
          {ticket.resolution_summary && (
            <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
              <p className="font-medium">Resolution</p>
              <p>{ticket.resolution_summary}</p>
            </div>
          )}
          <section className="space-y-3" aria-label="Conversation">
            {ticket.messages.map((message) => (
              <ConversationMessage key={message.id} message={message} />
            ))}
          </section>
          {ticket.status !== "CLOSED" && (
            <div className="card p-4">
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">Manual reply</p>
              <MessageComposer
                onSend={(message) => addMessage.mutateAsync(message)}
                isSending={addMessage.isPending}
                error={addMessage.error}
                placeholder="Write a reply to the customer…"
              />
            </div>
          )}
        </div>
        <div className="xl:col-span-2">
          <AIAnalysisPanel ticketId={ticket.id} />
        </div>
      </div>

      <Modal
        open={resolveOpen}
        title="Resolve ticket"
        onClose={() => setResolveOpen(false)}
        footer={
          <>
            <button type="button" className="btn-secondary" onClick={() => setResolveOpen(false)}>Cancel</button>
            <button
              type="button"
              className="btn-primary"
              disabled={resolution.trim().length < 5 || resolveTicket.isPending}
              onClick={() =>
                resolveTicket.mutate(resolution.trim(), {
                  onSuccess: () => {
                    setResolveOpen(false);
                    setResolution("");
                  },
                })
              }
            >
              Mark resolved
            </button>
          </>
        }
      >
        <label htmlFor="resolution" className="label">Resolution summary</label>
        <textarea
          id="resolution"
          className="input min-h-[120px]"
          value={resolution}
          onChange={(e) => setResolution(e.target.value)}
          placeholder="What was the root cause and how was it fixed? This is used to help with similar future tickets."
        />
        {Boolean(resolveTicket.error) && (
          <div className="mt-2">
            <ErrorMessage error={resolveTicket.error} />
          </div>
        )}
      </Modal>
    </div>
  );
}
