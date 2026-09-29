import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "../api/analytics";

export function useTicketAnalytics() {
  return useQuery({ queryKey: ["analytics", "tickets"], queryFn: analyticsApi.tickets });
}

export function useAIAnalytics() {
  return useQuery({ queryKey: ["analytics", "ai"], queryFn: analyticsApi.ai });
}
