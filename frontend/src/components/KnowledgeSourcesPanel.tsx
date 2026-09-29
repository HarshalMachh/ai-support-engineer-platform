import { useState } from "react";
import type { KnowledgeResult } from "../types";
import { formatPercent } from "../utils/format";

interface KnowledgeSourcesPanelProps {
  results: KnowledgeResult[];
  citedSources?: string[];
}

export function KnowledgeSourcesPanel({ results, citedSources = [] }: KnowledgeSourcesPanelProps) {
  const [expanded, setExpanded] = useState<number | null>(null);

  return (
    <section className="card">
      <div className="card-header">
        <h3 className="card-title">Retrieved documentation</h3>
        <span className="text-xs text-slate-500">{results.length} chunks</span>
      </div>
      {results.length === 0 ? (
        <p className="px-4 py-3 text-sm text-slate-500">No relevant knowledge base content was found.</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {results.map((result) => {
            const cited = citedSources.includes(result.document_title);
            const isOpen = expanded === result.chunk_id;
            return (
              <li key={result.chunk_id} className="px-4 py-2.5">
                <button
                  type="button"
                  className="flex w-full items-center justify-between gap-2 text-left"
                  onClick={() => setExpanded(isOpen ? null : result.chunk_id)}
                  aria-expanded={isOpen}
                >
                  <span className="text-sm font-medium text-slate-800">
                    {result.document_title}
                    <span className="ml-2 font-mono text-xs font-normal text-slate-400">
                      {result.filename} · chunk {result.chunk_index}
                    </span>
                  </span>
                  <span className="flex shrink-0 items-center gap-2">
                    {cited && <span className="badge bg-emerald-50 text-emerald-700 ring-emerald-600/20">cited</span>}
                    <span className="font-mono text-xs text-slate-500">{formatPercent(result.similarity)}</span>
                  </span>
                </button>
                {isOpen && (
                  <p className="mt-2 whitespace-pre-wrap rounded bg-slate-50 p-2 font-mono text-xs text-slate-700">
                    {result.content}
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
