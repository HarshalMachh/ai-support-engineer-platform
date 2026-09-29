import type { KnowledgeDocument, KnowledgeDocumentDetail, KnowledgeSearchResponse } from "../types";
import { apiClient } from "./client";

export const knowledgeApi = {
  list: () => apiClient.get<KnowledgeDocument[]>("/knowledge/documents").then((r) => r.data),
  get: (documentId: number) =>
    apiClient.get<KnowledgeDocumentDetail>(`/knowledge/documents/${documentId}`).then((r) => r.data),
  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    // Embedding a large document locally can take a while.
    return apiClient
      .post<KnowledgeDocument>("/knowledge/documents", form, { timeout: 180_000 })
      .then((r) => r.data);
  },
  remove: (documentId: number) => apiClient.delete(`/knowledge/documents/${documentId}`).then(() => undefined),
  search: (query: string, topK = 5) =>
    apiClient.post<KnowledgeSearchResponse>("/knowledge/search", { query, top_k: topK }).then((r) => r.data),
};
