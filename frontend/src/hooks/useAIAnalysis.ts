import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { aiApi } from "../api/ai";
import { ticketKeys } from "./useTickets";

export const aiKeys = {
  analysis: (ticketId: number) => ["ai-analysis", ticketId] as const,
};

const POLL_WHILE_RUNNING_MS = 2_500;

/** Latest AI analysis. Polls while a run is in progress (fallback if the WebSocket is unavailable). */
export function useAIAnalysis(ticketId: number) {
  return useQuery({
    queryKey: aiKeys.analysis(ticketId),
    queryFn: () => aiApi.getAnalysis(ticketId),
    enabled: Number.isFinite(ticketId),
    refetchInterval: (query) =>
      query.state.data?.analysis_status === "RUNNING" ? POLL_WHILE_RUNNING_MS : false,
  });
}

function useRefreshTicketAndAnalysis(ticketId: number) {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: aiKeys.analysis(ticketId) });
    void queryClient.invalidateQueries({ queryKey: ticketKeys.detail(ticketId) });
    void queryClient.invalidateQueries({ queryKey: ["tickets", "list"] });
    void queryClient.invalidateQueries({ queryKey: ["analytics"] });
  };
}

export function useAIActions(ticketId: number) {
  const refresh = useRefreshTicketAndAnalysis(ticketId);
  return {
    analyze: useMutation({ mutationFn: () => aiApi.analyze(ticketId), onSuccess: refresh }),
    regenerate: useMutation({ mutationFn: () => aiApi.regenerate(ticketId), onSuccess: refresh }),
    approve: useMutation({
      mutationFn: (editedResponse?: string) => aiApi.approve(ticketId, editedResponse),
      onSuccess: refresh,
    }),
    reject: useMutation({ mutationFn: (reason?: string) => aiApi.reject(ticketId, reason), onSuccess: refresh }),
    saveEdit: useMutation({
      mutationFn: (editedResponse: string) => aiApi.edit(ticketId, editedResponse),
      onSuccess: refresh,
    }),
    feedback: useMutation({
      mutationFn: ({ rating, comments }: { rating: number; comments?: string }) =>
        aiApi.feedback(ticketId, rating, comments),
    }),
  };
}

export type AIActions = ReturnType<typeof useAIActions>;
