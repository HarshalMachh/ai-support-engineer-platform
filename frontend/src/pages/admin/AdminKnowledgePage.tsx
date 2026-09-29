import { useRef, useState, type FormEvent } from "react";
import { ErrorMessage } from "../../components/ErrorMessage";
import { KnowledgeSourcesPanel } from "../../components/KnowledgeSourcesPanel";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { Modal } from "../../components/Modal";
import {
  useDeleteDocument,
  useKnowledgeDocument,
  useKnowledgeDocuments,
  useKnowledgeSearch,
  useUploadDocument,
} from "../../hooks/useKnowledge";
import type { KnowledgeDocument } from "../../types";
import { formatBytes, formatDateTime } from "../../utils/format";

const ALLOWED_EXTENSIONS = [".md", ".txt"];
const MAX_BYTES = 1_000_000;

function validateFile(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext))) return "Only .md and .txt files are supported.";
  if (file.size === 0) return "The file is empty.";
  if (file.size > MAX_BYTES) return "The file is larger than 1 MB.";
  return null;
}

export function AdminKnowledgePage() {
  const documents = useKnowledgeDocuments();
  const upload = useUploadDocument();
  const remove = useDeleteDocument();
  const search = useKnowledgeSearch();
  const fileInput = useRef<HTMLInputElement>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [viewingId, setViewingId] = useState<number | null>(null);
  const [deleting, setDeleting] = useState<KnowledgeDocument | null>(null);
  const viewing = useKnowledgeDocument(viewingId);

  const handleFile = (file: File | undefined) => {
    if (!file) return;
    const error = validateFile(file);
    setFileError(error);
    if (!error) {
      upload.mutate(file, {
        onSettled: () => {
          if (fileInput.current) fileInput.current.value = "";
        },
      });
    }
  };

  const handleSearch = (event: FormEvent) => {
    event.preventDefault();
    if (query.trim().length >= 2) search.mutate(query.trim());
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Knowledge base</h1>
        <p className="text-sm text-slate-500">
          Documents are cleaned, split into overlapping chunks, embedded locally and stored in pgvector for retrieval.
        </p>
      </div>

      <section className="card p-4">
        <div className="flex flex-wrap items-center gap-3">
          <input
            ref={fileInput}
            type="file"
            accept=".md,.txt,text/markdown,text/plain"
            aria-label="Upload document"
            className="text-sm file:mr-3 file:rounded-md file:border-0 file:bg-brand-600 file:px-3 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-brand-700"
            onChange={(e) => handleFile(e.target.files?.[0])}
            disabled={upload.isPending}
          />
          {upload.isPending && <LoadingSpinner size="sm" label="Uploading and embedding…" />}
          {upload.isSuccess && !upload.isPending && (
            <span className="text-sm text-emerald-700">
              Indexed “{upload.data.title}” ({upload.data.chunk_count} chunks)
            </span>
          )}
        </div>
        <div className="mt-3 space-y-2">
          {fileError && <ErrorMessage message={fileError} title="Invalid file" />}
          {Boolean(upload.error) && <ErrorMessage error={upload.error} title="Upload failed" />}
        </div>
      </section>

      <section className="card">
        <div className="card-header">
          <h2 className="card-title">Documents</h2>
          <span className="text-xs text-slate-500">{documents.data?.length ?? 0} total</span>
        </div>
        {documents.isLoading && <LoadingSpinner className="p-4" />}
        {documents.isError && (
          <div className="p-4">
            <ErrorMessage error={documents.error} />
          </div>
        )}
        {documents.data && documents.data.length === 0 && (
          <p className="px-4 py-6 text-center text-sm text-slate-500">
            No documents yet. Upload one above or run the seed script.
          </p>
        )}
        {documents.data && documents.data.length > 0 && (
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2">Title</th>
                <th className="px-4 py-2">File</th>
                <th className="px-4 py-2">Chunks</th>
                <th className="px-4 py-2">Size</th>
                <th className="px-4 py-2">Embedding model</th>
                <th className="px-4 py-2">Uploaded</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {documents.data.map((doc) => (
                <tr key={doc.id}>
                  <td className="px-4 py-2.5 font-medium">{doc.title}</td>
                  <td className="px-4 py-2.5 font-mono text-xs">{doc.filename}</td>
                  <td className="px-4 py-2.5 tabular-nums">{doc.chunk_count}</td>
                  <td className="px-4 py-2.5">{formatBytes(doc.size_bytes)}</td>
                  <td className="px-4 py-2.5 font-mono text-xs">{doc.embedding_model}</td>
                  <td className="px-4 py-2.5 text-slate-500">{formatDateTime(doc.created_at)}</td>
                  <td className="space-x-1 whitespace-nowrap px-4 py-2.5 text-right">
                    <button type="button" className="btn-ghost py-1" onClick={() => setViewingId(doc.id)}>
                      View
                    </button>
                    <button type="button" className="btn-ghost py-1 text-rose-600" onClick={() => setDeleting(doc)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="space-y-3">
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            className="input"
            placeholder="Test semantic search, e.g. “how do refunds work for annual plans?”"
            aria-label="Semantic search query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="submit" className="btn-secondary" disabled={search.isPending || query.trim().length < 2}>
            {search.isPending ? "Searching…" : "Search"}
          </button>
        </form>
        {Boolean(search.error) && <ErrorMessage error={search.error} title="Search failed" />}
        {search.data && <KnowledgeSourcesPanel results={search.data.results} />}
      </section>

      <Modal open={viewingId !== null} title={viewing.data?.title ?? "Document"} onClose={() => setViewingId(null)} size="lg">
        {viewing.isLoading && <LoadingSpinner />}
        {viewing.isError && <ErrorMessage error={viewing.error} />}
        {viewing.data && (
          <div className="space-y-3">
            {viewing.data.chunks.map((chunk) => (
              <div key={chunk.id} className="rounded border border-slate-200">
                <p className="border-b border-slate-100 bg-slate-50 px-3 py-1 font-mono text-xs text-slate-500">
                  chunk {chunk.chunk_index}
                </p>
                <p className="whitespace-pre-wrap px-3 py-2 text-sm">{chunk.content}</p>
              </div>
            ))}
          </div>
        )}
      </Modal>

      <Modal
        open={deleting !== null}
        title="Delete document?"
        onClose={() => setDeleting(null)}
        footer={
          <>
            <button type="button" className="btn-secondary" onClick={() => setDeleting(null)}>Cancel</button>
            <button
              type="button"
              className="btn-danger"
              disabled={remove.isPending}
              onClick={() => deleting && remove.mutate(deleting.id, { onSuccess: () => setDeleting(null) })}
            >
              Delete
            </button>
          </>
        }
      >
        <p className="text-sm text-slate-600">
          “{deleting?.title}” and all of its chunks will be removed from the knowledge base.
        </p>
        {Boolean(remove.error) && <ErrorMessage error={remove.error} />}
      </Modal>
    </div>
  );
}
