import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { websocketUrl } from "../api/client";
import type { AIProgressEvent } from "../types";
import { tokenStorage } from "../utils/tokenStorage";
import { aiKeys } from "./useAIAnalysis";
import { ticketKeys } from "./useTickets";

interface ProgressMessage extends Partial<AIProgressEvent> {
  type: "progress" | "done";
  status?: string;
}

/**
 * Streams live AI progress over a WebSocket while `active` is true.
 * If the socket fails, `useAIAnalysis` polling still keeps the UI up to date.
 */
export function useAIProgress(ticketId: number, active: boolean) {
  const queryClient = useQueryClient();
  const [events, setEvents] = useState<AIProgressEvent[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const token = tokenStorage.get();
    if (!active || !token || typeof WebSocket === "undefined") return;

    setEvents([]);
    const socket = new WebSocket(
      websocketUrl(`/ws/tickets/${ticketId}/ai-progress?token=${encodeURIComponent(token)}`),
    );
    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onmessage = (message) => {
      const data = JSON.parse(message.data as string) as ProgressMessage;
      if (data.type === "progress" && data.event && data.message && data.timestamp) {
        const event: AIProgressEvent = { event: data.event, message: data.message, timestamp: data.timestamp };
        setEvents((current) => [...current, event]);
      }
      if (data.type === "done" || data.event === "response_generated" || data.event === "analysis_failed") {
        void queryClient.invalidateQueries({ queryKey: aiKeys.analysis(ticketId) });
        void queryClient.invalidateQueries({ queryKey: ticketKeys.detail(ticketId) });
      }
    };
    return () => socket.close();
  }, [ticketId, active, queryClient]);

  return { events, connected };
}
