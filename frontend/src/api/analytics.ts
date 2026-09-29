import type { AIAnalytics, TicketAnalytics } from "../types";
import { apiClient } from "./client";

export const analyticsApi = {
  tickets: () => apiClient.get<TicketAnalytics>("/analytics/tickets").then((r) => r.data),
  ai: () => apiClient.get<AIAnalytics>("/analytics/ai").then((r) => r.data),
};
