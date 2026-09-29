import type { AIAnalysis, AIFeedback, AIResponse, AnalysisStarted } from "../types";
import { apiClient } from "./client";

export const aiApi = {
  analyze: (ticketId: number) =>
    apiClient.post<AnalysisStarted>(`/tickets/${ticketId}/analyze`).then((r) => r.data),
  getAnalysis: (ticketId: number) =>
    apiClient.get<AIAnalysis>(`/tickets/${ticketId}/ai-analysis`).then((r) => r.data),
  regenerate: (ticketId: number) =>
    apiClient.post<AnalysisStarted>(`/tickets/${ticketId}/ai-response/regenerate`).then((r) => r.data),
  approve: (ticketId: number, editedResponse?: string) =>
    apiClient
      .post<AIResponse>(
        `/tickets/${ticketId}/ai-response/approve`,
        editedResponse ? { edited_response: editedResponse } : {},
      )
      .then((r) => r.data),
  reject: (ticketId: number, reason?: string) =>
    apiClient.post<AIResponse>(`/tickets/${ticketId}/ai-response/reject`, { reason: reason || null }).then((r) => r.data),
  edit: (ticketId: number, editedResponse: string) =>
    apiClient
      .patch<AIResponse>(`/tickets/${ticketId}/ai-response`, { edited_response: editedResponse })
      .then((r) => r.data),
  feedback: (ticketId: number, rating: number, comments?: string) =>
    apiClient
      .post<AIFeedback>(`/tickets/${ticketId}/ai-feedback`, { rating, comments: comments || null })
      .then((r) => r.data),
};
