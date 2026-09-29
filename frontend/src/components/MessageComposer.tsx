import { useState, type FormEvent } from "react";
import { ErrorMessage } from "./ErrorMessage";

interface MessageComposerProps {
  onSend: (message: string) => Promise<unknown>;
  isSending: boolean;
  error?: unknown;
  placeholder?: string;
  disabled?: boolean;
}

export function MessageComposer({ onSend, isSending, error, placeholder = "Write a reply…", disabled }: MessageComposerProps) {
  const [text, setText] = useState("");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!text.trim()) return;
    try {
      await onSend(text.trim());
      setText("");
    } catch {
      // Error is surfaced through the `error` prop.
    }
  };

  return (
    <form onSubmit={submit} className="space-y-2">
      {Boolean(error) && <ErrorMessage error={error} title="Message not sent" />}
      <textarea
        className="input min-h-[96px]"
        aria-label="Reply"
        placeholder={placeholder}
        value={text}
        disabled={disabled}
        onChange={(event) => setText(event.target.value)}
      />
      <div className="flex justify-end">
        <button type="submit" className="btn-primary" disabled={disabled || isSending || !text.trim()}>
          {isSending ? "Sending…" : "Send reply"}
        </button>
      </div>
    </form>
  );
}
