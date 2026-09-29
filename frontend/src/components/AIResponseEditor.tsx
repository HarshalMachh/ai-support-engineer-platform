import { useEffect, useState } from "react";
import type { AIResponse } from "../types";
import { formatDateTime, formatPercent } from "../utils/format";
import { ErrorMessage } from "./ErrorMessage";

interface AIResponseEditorProps {
  response: AIResponse;
  onApprove: (editedText?: string) => Promise<unknown>;
  onSaveEdit: (text: string) => Promise<unknown>;
  onReject: (reason?: string) => Promise<unknown>;
  onRegenerate: () => Promise<unknown>;
  isBusy?: boolean;
  error?: unknown;
}

const STATUS_NOTES: Record<AIResponse["status"], string> = {
  PENDING: "Awaiting human review. Nothing has been sent to the customer.",
  APPROVED: "Approved and sent to the customer without changes.",
  EDITED: "Edited by an agent and sent to the customer.",
  REJECTED: "Rejected. This draft was not sent.",
  SUPERSEDED: "Replaced by a newer draft.",
};

export function AIResponseEditor({
  response,
  onApprove,
  onSaveEdit,
  onReject,
  onRegenerate,
  isBusy = false,
  error,
}: AIResponseEditorProps) {
  const initialText = response.edited_response ?? response.generated_response;
  const [text, setText] = useState(initialText);
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");

  useEffect(() => {
    setText(response.edited_response ?? response.generated_response);
    setRejecting(false);
    setReason("");
  }, [response.id, response.edited_response, response.generated_response]);

  const isPending = response.status === "PENDING";
  const changedFromDraft = text.trim() !== response.generated_response.trim();
  const unsavedChanges = text.trim() !== initialText.trim();

  const run = (action: () => Promise<unknown>) => () => {
    action().catch(() => undefined);
  };

  return (
    <section className="card" aria-label="AI response editor">
      <div className="card-header">
        <h3 className="card-title">Suggested response</h3>
        <span className="font-mono text-xs text-slate-500">
          confidence {formatPercent(response.confidence_score)} · {response.model_name}
        </span>
      </div>
      <div className="space-y-3 px-4 py-3">
        <p
          className={`rounded-md px-3 py-2 text-xs ${
            isPending ? "bg-amber-50 text-amber-800" : "bg-slate-50 text-slate-600"
          }`}
        >
          <strong className="font-semibold">{response.status}</strong> — {STATUS_NOTES[response.status]}
          {response.approver && ` Reviewed by ${response.approver.name}, ${formatDateTime(response.updated_at)}.`}
        </p>

        {response.requires_more_information && (
          <div className="rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900">
            <p className="font-medium">The AI needs more information. Consider asking for:</p>
            <ul className="ml-5 mt-1 list-disc">
              {response.requested_information.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        )}

        {Boolean(error) && <ErrorMessage error={error} title="Action failed" />}

        {isPending ? (
          <textarea
            className="input min-h-[180px] font-sans leading-relaxed"
            aria-label="Draft response"
            value={text}
            onChange={(event) => setText(event.target.value)}
            disabled={isBusy}
          />
        ) : (
          <p className="whitespace-pre-wrap rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
            {response.edited_response ?? response.generated_response}
          </p>
        )}

        {response.rejection_reason && (
          <p className="text-xs text-slate-500">Rejection reason: {response.rejection_reason}</p>
        )}

        {isPending && rejecting && (
          <div className="space-y-2 rounded-md border border-rose-200 bg-rose-50 p-3">
            <label className="label" htmlFor="reject-reason">
              Why is this draft being rejected? (optional)
            </label>
            <input
              id="reject-reason"
              className="input"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
            <div className="flex gap-2">
              <button
                type="button"
                className="btn-danger"
                disabled={isBusy}
                onClick={run(() => onReject(reason.trim() || undefined))}
              >
                Confirm reject
              </button>
              <button type="button" className="btn-ghost" onClick={() => setRejecting(false)}>
                Cancel
              </button>
            </div>
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          {isPending && (
            <>
              <button
                type="button"
                className="btn-primary"
                disabled={isBusy || !text.trim()}
                onClick={run(() => onApprove(changedFromDraft ? text.trim() : undefined))}
              >
                {changedFromDraft ? "Approve edited & send" : "Approve & send"}
              </button>
              <button
                type="button"
                className="btn-secondary"
                disabled={isBusy || !unsavedChanges || !text.trim()}
                onClick={run(() => onSaveEdit(text.trim()))}
              >
                Save edit
              </button>
              <button
                type="button"
                className="btn-secondary text-rose-700"
                disabled={isBusy}
                onClick={() => setRejecting(true)}
              >
                Reject
              </button>
            </>
          )}
          <button type="button" className="btn-ghost" disabled={isBusy} onClick={run(onRegenerate)}>
            Regenerate
          </button>
        </div>
        <p className="text-xs text-slate-400">
          AI drafts are never sent automatically. Only an approved or edited draft is added to the conversation.
        </p>
      </div>
    </section>
  );
}
