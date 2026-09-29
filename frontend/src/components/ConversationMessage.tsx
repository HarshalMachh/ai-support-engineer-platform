import type { TicketMessage } from "../types";
import { formatDateTime } from "../utils/format";

const TYPE_STYLES: Record<TicketMessage["message_type"], { container: string; label: string }> = {
  CUSTOMER: { container: "border-slate-200 bg-white", label: "Customer" },
  AGENT: { container: "border-brand-200 bg-brand-50", label: "Support" },
  AI_DRAFT: { container: "border-dashed border-violet-300 bg-violet-50", label: "AI draft · internal" },
  SYSTEM: { container: "border-slate-200 bg-slate-50 text-slate-600", label: "System" },
};

export function ConversationMessage({ message }: { message: TicketMessage }) {
  const style = TYPE_STYLES[message.message_type];
  return (
    <article className={`rounded-lg border px-4 py-3 ${style.container}`}>
      <header className="mb-1 flex flex-wrap items-center gap-x-2 text-xs text-slate-500">
        <span className="font-semibold text-slate-800">{message.sender?.name ?? "AI Assistant"}</span>
        <span className="rounded bg-white/70 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide ring-1 ring-slate-200">
          {style.label}
        </span>
        {message.ai_response_id && message.message_type === "AGENT" && (
          <span className="text-violet-600">AI-assisted, human approved</span>
        )}
        <time className="ml-auto" dateTime={message.created_at}>
          {formatDateTime(message.created_at)}
        </time>
      </header>
      <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.message}</p>
    </article>
  );
}
