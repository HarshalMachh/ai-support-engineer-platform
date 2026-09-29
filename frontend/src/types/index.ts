// Mirrors the Pydantic schemas in backend/app/schemas.

export type UserRole = "CUSTOMER" | "AGENT" | "ADMIN";

export const TICKET_STATUSES = ["OPEN", "IN_PROGRESS", "WAITING_FOR_CUSTOMER", "RESOLVED", "CLOSED"] as const;
export type TicketStatus = (typeof TICKET_STATUSES)[number];

export const TICKET_PRIORITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;
export type TicketPriority = (typeof TICKET_PRIORITIES)[number];

export const TICKET_CATEGORIES = [
  "AUTHENTICATION",
  "BILLING",
  "ACCOUNT",
  "API",
  "PERFORMANCE",
  "BUG",
  "FEATURE_REQUEST",
  "OTHER",
] as const;
export type TicketCategory = (typeof TICKET_CATEGORIES)[number];

export const ENVIRONMENTS = ["production", "staging", "development", "local"] as const;

export type MessageType = "CUSTOMER" | "AGENT" | "AI_DRAFT" | "SYSTEM";
export type AIResponseStatus = "PENDING" | "APPROVED" | "EDITED" | "REJECTED" | "SUPERSEDED";
export type AIAnalysisStatus = "IDLE" | "RUNNING" | "COMPLETED" | "FAILED";

export interface UserBrief {
  id: number;
  name: string;
  email: string;
  role: UserRole;
}

export interface User extends UserBrief {
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface TicketMessage {
  id: number;
  ticket_id: number;
  sender: UserBrief | null;
  message: string;
  message_type: MessageType;
  ai_response_id: number | null;
  created_at: string;
}

export interface TicketSummary {
  id: number;
  subject: string;
  environment: string;
  category: TicketCategory | null;
  priority: TicketPriority | null;
  status: TicketStatus;
  ai_confidence: number | null;
  ai_analysis_status: AIAnalysisStatus;
  customer: UserBrief;
  assigned_agent: UserBrief | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export interface TicketDetail extends TicketSummary {
  description: string;
  resolution_summary: string | null;
  ai_error: string | null;
  messages: TicketMessage[];
}

export interface TicketFilters {
  status?: TicketStatus | "";
  priority?: TicketPriority | "";
  category?: TicketCategory | "";
  assigned_agent?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface TicketCreatePayload {
  subject: string;
  description: string;
  environment: string;
}

export interface TicketUpdatePayload {
  status?: TicketStatus;
  priority?: TicketPriority;
  category?: TicketCategory;
  assigned_agent_id?: number | null;
}

export interface KnowledgeResult {
  chunk_id: number;
  document_id: number;
  document_title: string;
  filename: string;
  chunk_index: number;
  content: string;
  similarity: number;
}

export interface SimilarTicket {
  ticket_id: number;
  subject: string;
  similarity: number;
  resolution_summary: string;
}

export interface AIProgressEvent {
  event: string;
  message: string;
  timestamp: string;
}

export interface AIResponse {
  id: number;
  ticket_id: number;
  generated_response: string;
  edited_response: string | null;
  reasoning_summary: string;
  confidence_score: number;
  status: AIResponseStatus;
  approver: UserBrief | null;
  category: TicketCategory | null;
  classification_confidence: number | null;
  priority: TicketPriority | null;
  priority_reason: string | null;
  requires_more_information: boolean;
  requested_information: string[];
  source_references: string[];
  knowledge_results: KnowledgeResult[];
  similar_tickets: SimilarTicket[];
  warnings: string[];
  model_name: string;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface AIAnalysis {
  ticket_id: number;
  analysis_status: AIAnalysisStatus;
  error: string | null;
  progress: AIProgressEvent[];
  latest_response: AIResponse | null;
}

export interface AnalysisStarted {
  ticket_id: number;
  analysis_status: AIAnalysisStatus;
  message: string;
}

export interface AIFeedback {
  id: number;
  ai_response_id: number;
  agent_id: number | null;
  rating: number;
  comments: string | null;
  created_at: string;
}

export interface KnowledgeDocument {
  id: number;
  title: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  embedding_model: string;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeDocumentDetail extends KnowledgeDocument {
  content: string;
  chunks: { id: number; chunk_index: number; content: string }[];
}

export interface KnowledgeSearchResponse {
  query: string;
  results: KnowledgeResult[];
}

export interface TicketAnalytics {
  total_tickets: number;
  open_tickets: number;
  in_progress_tickets: number;
  waiting_for_customer_tickets: number;
  critical_tickets: number;
  resolved_tickets: number;
  closed_tickets: number;
  unassigned_tickets: number;
  tickets_by_category: Record<string, number>;
  tickets_by_priority: Record<string, number>;
  tickets_by_status: Record<string, number>;
  average_resolution_time_hours: number | null;
}

export interface AIAnalytics {
  total_responses: number;
  pending_count: number;
  approved_count: number;
  edited_count: number;
  rejected_count: number;
  superseded_count: number;
  approval_rate: number | null;
  acceptance_rate: number | null;
  average_confidence: number | null;
  average_feedback_rating: number | null;
  feedback_count: number;
}

export interface ApiErrorBody {
  detail?: string | { msg: string }[];
  code?: string;
}
