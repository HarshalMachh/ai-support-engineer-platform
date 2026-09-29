import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ticketsApi } from "../api/tickets";
import type { TicketCreatePayload, TicketDetail, TicketFilters, TicketUpdatePayload } from "../types";

export const ticketKeys = {
  all: ["tickets"] as const,
  list: (filters: TicketFilters) => ["tickets", "list", filters] as const,
  detail: (ticketId: number) => ["tickets", "detail", ticketId] as const,
};

export function useTickets(filters: TicketFilters) {
  return useQuery({
    queryKey: ticketKeys.list(filters),
    queryFn: () => ticketsApi.list(filters),
    placeholderData: keepPreviousData,
  });
}

export function useTicket(ticketId: number, options: { refetchInterval?: number | false } = {}) {
  return useQuery({
    queryKey: ticketKeys.detail(ticketId),
    queryFn: () => ticketsApi.get(ticketId),
    enabled: Number.isFinite(ticketId),
    refetchInterval: options.refetchInterval,
  });
}

/** Shared onSuccess: store the fresh ticket and refresh any lists. */
function useTicketUpdater() {
  const queryClient = useQueryClient();
  return (ticket: TicketDetail) => {
    queryClient.setQueryData(ticketKeys.detail(ticket.id), ticket);
    void queryClient.invalidateQueries({ queryKey: ["tickets", "list"] });
    void queryClient.invalidateQueries({ queryKey: ["analytics"] });
  };
}

export function useCreateTicket() {
  const onSuccess = useTicketUpdater();
  return useMutation({ mutationFn: (payload: TicketCreatePayload) => ticketsApi.create(payload), onSuccess });
}

export function useUpdateTicket(ticketId: number) {
  const onSuccess = useTicketUpdater();
  return useMutation({
    mutationFn: (payload: TicketUpdatePayload) => ticketsApi.update(ticketId, payload),
    onSuccess,
  });
}

export function useAddMessage(ticketId: number) {
  const onSuccess = useTicketUpdater();
  return useMutation({ mutationFn: (message: string) => ticketsApi.addMessage(ticketId, message), onSuccess });
}

export function useAssignTicket(ticketId: number) {
  const onSuccess = useTicketUpdater();
  return useMutation({ mutationFn: (agentId?: number) => ticketsApi.assign(ticketId, agentId), onSuccess });
}

export function useResolveTicket(ticketId: number) {
  const onSuccess = useTicketUpdater();
  return useMutation({
    mutationFn: (resolutionSummary: string) => ticketsApi.resolve(ticketId, resolutionSummary),
    onSuccess,
  });
}
