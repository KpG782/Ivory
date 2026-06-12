export type ChatRole = "user" | "assistant" | "system";

export interface BookingResult {
  product_type?: string;
  premium?: number;
  annual_premium?: number;
  currency?: string;
  summary?: string;
  coverage_level?: string;
  term_years?: string | number;
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
  has_booking_result?: boolean;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  streaming?: boolean;
  bookingResult?: BookingResult | null;
  kind?: "normal" | "error" | "info";
}

export interface SavedChatSession {
  sessionId: string;
  label: string;
  preview: string;
  updatedAt: string;
  messages: ChatMessage[];
  sessionSnapshot: SessionSnapshot | null;
  bookingResult: BookingResult | null;
}

export interface SseEvent {
  event: string;
  data: string;
}
