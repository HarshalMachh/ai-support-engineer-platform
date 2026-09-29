import type {
  Page,
  TicketCreatePayload,
  TicketDetail,
  TicketFilters,
  TicketSummary,
  TicketUpdatePayload,
} from "../types";
import { apiClient } from "./client";

function cleanParams(filters: TicketFilters): Record<string, string | number> {
  return Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== undefined && value !== null && value !== ""),
  ) as Record<string, string | number>;
}

export const ticketsApi = {
  list: (filters: TicketFilters) =>
    apiClient.get<Page<TicketSummary>>("/tickets", { params: cleanParams(filters) }).then((r) => r.data),
  get: (ticketId: number) => apiClient.get<TicketDetail>(`/tickets/${ticketId}`).then((r) => r.data),
  create: (payload: TicketCreatePayload) => apiClient.post<TicketDetail>("/tickets", payload).then((r) => r.data),
  update: (ticketId: number, payload: TicketUpdatePayload) =>
    apiClient.patch<TicketDetail>(`/tickets/${ticketId}`, payload).then((r) => r.data),
  addMessage: (ticketId: number, message: string) =>
    apiClient.post<TicketDetail>(`/tickets/${ticketId}/messages`, { message }).then((r) => r.data),
  assign: (ticketId: number, agentId?: number) =>
    apiClient
      .post<TicketDetail>(`/tickets/${ticketId}/assign`, agentId ? { agent_id: agentId } : {})
      .then((r) => r.data),
  resolve: (ticketId: number, resolutionSummary: string) =>
    apiClient
      .post<TicketDetail>(`/tickets/${ticketId}/resolve`, { resolution_summary: resolutionSummary })
      .then((r) => r.data),
};
