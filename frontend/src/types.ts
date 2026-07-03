export type ChatRole = "user" | "assistant" | "system";

export interface VisitEstimate {
  service_type?: string;
  estimate_low?: number;
  estimate_high?: number;
  currency?: string;
  summary?: string;
  [key: string]: unknown;
}

export interface SessionSnapshot {
  session_id?: string;
  mode?: string;
  intent?: string;
  intake_step?: string;
  service_type?: string | null;
  current_field?: string | null;
  trace_id?: string | null;
  has_visit_estimate?: boolean;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  streaming?: boolean;
  visitEstimate?: VisitEstimate | null;
  kind?: "normal" | "error" | "info";
}

export interface SavedChatSession {
  sessionId: string;
  label: string;
  preview: string;
  updatedAt: string;
  messages: ChatMessage[];
  sessionSnapshot: SessionSnapshot | null;
  visitEstimate: VisitEstimate | null;
}

export interface SseEvent {
  event: string;
  data: string;
}
