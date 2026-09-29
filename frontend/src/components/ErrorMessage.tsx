import { getErrorMessage } from "../utils/errors";

interface ErrorMessageProps {
  error?: unknown;
  message?: string;
  title?: string;
  onRetry?: () => void;
}

export function ErrorMessage({ error, message, title = "Error", onRetry }: ErrorMessageProps) {
  const text = message ?? getErrorMessage(error);
  return (
    <div role="alert" className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-semibold">{title}</p>
          <p className="mt-0.5">{text}</p>
        </div>
        {onRetry && (
          <button type="button" className="btn-secondary shrink-0 py-1 text-xs" onClick={onRetry}>
            Retry
          </button>
        )}
      </div>
    </div>
  );
}
