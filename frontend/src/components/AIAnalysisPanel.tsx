import { useState } from "react";
import { useAIActions, useAIAnalysis } from "../hooks/useAIAnalysis";
import { useAIProgress } from "../hooks/useAIProgress";
import type { AIProgressEvent, AIResponse } from "../types";
import { getErrorCode } from "../utils/errors";
import { formatPercent } from "../utils/format";
import { AIResponseEditor } from "./AIResponseEditor";
import { CategoryBadge } from "./CategoryBadge";
import { ErrorMessage } from "./ErrorMessage";
import { KnowledgeSourcesPanel } from "./KnowledgeSourcesPanel";
import { LoadingSpinner } from "./LoadingSpinner";
import { PriorityBadge } from "./PriorityBadge";
import { SimilarTicketsPanel } from "./SimilarTicketsPanel";

const OLLAMA_HELP =
  "Make sure Ollama is running on the host (`ollama serve`) and the models are pulled " +
  "(`ollama pull qwen2.5:7b` and `ollama pull nomic-embed-text`), then click Analyze again.";

function ProgressList({ events }: { events: AIProgressEvent[] }) {
  if (events.length === 0) return <LoadingSpinner label="Starting AI workflow…" size="sm" />;
  return (
    <ol className="space-y-1 font-mono text-xs text-slate-600">
      {events.map((event, index) => (
        <li key={`${event.event}-${index}`} className="flex gap-2">
          <span className="text-emerald-600">✓</span>
          <span className="text-slate-400">{event.event}</span>
          <span>{event.message}</span>
        </li>
      ))}
    </ol>
  );
}

function AnalysisSummary({ response }: { response: AIResponse }) {
  return (
    <section className="card">
      <div className="card-header">
        <h3 className="card-title">AI triage</h3>
        <span className="text-xs text-slate-500">human review required</span>
      </div>
      <dl className="grid grid-cols-1 gap-3 px-4 py-3 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-xs uppercase tracking-wide text-slate-500">Classification</dt>
          <dd className="mt-1 flex items-center gap-2">
            <CategoryBadge category={response.category} />
            <span className="font-mono text-xs text-slate-500">{formatPercent(response.classification_confidence)}</span>
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-slate-500">Priority</dt>
          <dd className="mt-1">
            <PriorityBadge priority={response.priority} />
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-slate-500">Response confidence</dt>
          <dd className="mt-1 font-mono text-sm">{formatPercent(response.confidence_score)}</dd>
        </div>
        {response.priority_reason && (
          <div className="sm:col-span-3">
            <dt className="text-xs uppercase tracking-wide text-slate-500">Priority reasoning</dt>
            <dd className="mt-1 text-slate-700">{response.priority_reason}</dd>
          </div>
        )}
        {response.reasoning_summary && (
          <div className="sm:col-span-3">
            <dt className="text-xs uppercase tracking-wide text-slate-500">Reasoning summary</dt>
            <dd className="mt-1 text-slate-700">{response.reasoning_summary}</dd>
          </div>
        )}
        {response.source_references.length > 0 && (
          <div className="sm:col-span-3">
            <dt className="text-xs uppercase tracking-wide text-slate-500">Sources cited</dt>
            <dd className="mt-1 flex flex-wrap gap-1">
              {response.source_references.map((source) => (
                <span key={source} className="badge bg-slate-50 text-slate-700 ring-slate-300">
                  {source}
                </span>
              ))}
            </dd>
          </div>
        )}
      </dl>
      {response.warnings.length > 0 && (
        <ul className="space-y-1 border-t border-slate-100 px-4 py-2 text-xs text-amber-700">
          {response.warnings.map((warning) => (
            <li key={warning}>⚠ {warning}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

function FeedbackForm({ ticketId }: { ticketId: number }) {
  const { feedback } = useAIActions(ticketId);
  const [rating, setRating] = useState(0);
  const [comments, setComments] = useState("");

  if (feedback.isSuccess) {
    return <p className="text-xs text-emerald-700">Thanks — feedback recorded.</p>;
  }
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <span className="text-slate-600">Rate this draft:</span>
      {[1, 2, 3, 4, 5].map((value) => (
        <button
          key={value}
          type="button"
          aria-label={`${value} star${value > 1 ? "s" : ""}`}
          className={`text-lg ${value <= rating ? "text-amber-500" : "text-slate-300"}`}
          onClick={() => setRating(value)}
        >
          ★
        </button>
      ))}
      <input
        className="input w-56 py-1"
        placeholder="Optional comment"
        value={comments}
        onChange={(e) => setComments(e.target.value)}
      />
      <button
        type="button"
        className="btn-secondary py-1"
        disabled={rating === 0 || feedback.isPending}
        onClick={() => feedback.mutate({ rating, comments: comments.trim() || undefined })}
      >
        Submit
      </button>
      {feedback.isError && <span className="text-xs text-rose-600">Could not save feedback.</span>}
    </div>
  );
}

export function AIAnalysisPanel({ ticketId }: { ticketId: number }) {
  const analysisQuery = useAIAnalysis(ticketId);
  const actions = useAIActions(ticketId);
  const analysis = analysisQuery.data;
  const isRunning = analysis?.analysis_status === "RUNNING";
  const live = useAIProgress(ticketId, isRunning);

  if (analysisQuery.isLoading) return <LoadingSpinner label="Loading AI analysis…" />;
  if (analysisQuery.isError) {
    return <ErrorMessage error={analysisQuery.error} title="Could not load AI analysis" onRetry={() => analysisQuery.refetch()} />;
  }
  if (!analysis) return null;

  const response = analysis.latest_response;
  const startError = actions.analyze.error ?? actions.regenerate.error;
  const reviewError = actions.approve.error ?? actions.reject.error ?? actions.saveEdit.error;
  const busy =
    isRunning ||
    actions.analyze.isPending ||
    actions.regenerate.isPending ||
    actions.approve.isPending ||
    actions.reject.isPending ||
    actions.saveEdit.isPending;
  const progressEvents = live.events.length > 0 ? live.events : analysis.progress;
  const ollamaProblem =
    getErrorCode(startError) === "ollama_unavailable" || /ollama/i.test(analysis.error ?? "");

  return (
    <div className="space-y-4">
      <section className="card">
        <div className="card-header">
          <h3 className="card-title">AI assistant</h3>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-slate-500">
              {analysis.analysis_status.toLowerCase()}
              {isRunning && (live.connected ? " · live" : " · polling")}
            </span>
            {!response && (
              <button
                type="button"
                className="btn-primary py-1"
                disabled={busy}
                onClick={() => actions.analyze.mutate()}
              >
                {isRunning ? "Analyzing…" : "Analyze ticket"}
              </button>
            )}
          </div>
        </div>
        <div className="space-y-3 px-4 py-3">
          {isRunning && <ProgressList events={progressEvents} />}
          {Boolean(startError) && <ErrorMessage error={startError} title="Could not start AI analysis" />}
          {analysis.analysis_status === "FAILED" && analysis.error && !isRunning && (
            <ErrorMessage message={analysis.error} title="AI analysis failed" />
          )}
          {ollamaProblem && <p className="text-xs text-slate-600">{OLLAMA_HELP}</p>}
          {!response && !isRunning && !startError && analysis.analysis_status !== "FAILED" && (
            <p className="text-sm text-slate-500">
              No AI analysis yet. The assistant will classify, prioritise, search the knowledge base and draft a reply
              for you to review.
            </p>
          )}
        </div>
      </section>

      {response && (
        <>
          <AnalysisSummary response={response} />
          <AIResponseEditor
            response={response}
            isBusy={busy}
            error={reviewError}
            onApprove={(edited) => actions.approve.mutateAsync(edited)}
            onSaveEdit={(text) => actions.saveEdit.mutateAsync(text)}
            onReject={(reason) => actions.reject.mutateAsync(reason)}
            onRegenerate={() => actions.regenerate.mutateAsync()}
          />
          <div className="card px-4 py-3">
            <FeedbackForm key={response.id} ticketId={ticketId} />
          </div>
          <KnowledgeSourcesPanel results={response.knowledge_results} citedSources={response.source_references} />
          <SimilarTicketsPanel tickets={response.similar_tickets} />
        </>
      )}
    </div>
  );
}
