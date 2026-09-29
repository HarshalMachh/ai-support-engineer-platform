import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { knowledgeApi } from "../api/knowledge";

const knowledgeKeys = {
  documents: ["knowledge", "documents"] as const,
  document: (id: number) => ["knowledge", "documents", id] as const,
};

export function useKnowledgeDocuments() {
  return useQuery({ queryKey: knowledgeKeys.documents, queryFn: knowledgeApi.list });
}

export function useKnowledgeDocument(documentId: number | null) {
  return useQuery({
    queryKey: knowledgeKeys.document(documentId ?? -1),
    queryFn: () => knowledgeApi.get(documentId as number),
    enabled: documentId !== null,
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => knowledgeApi.upload(file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: knowledgeKeys.documents }),
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: number) => knowledgeApi.remove(documentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: knowledgeKeys.documents }),
  });
}

export function useKnowledgeSearch() {
  return useMutation({ mutationFn: (query: string) => knowledgeApi.search(query) });
}
