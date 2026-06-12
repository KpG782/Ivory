"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  ChatMessage,
  BookingResult,
  SavedChatSession,
  SessionSnapshot
} from "../types";
import { parseSseData, parseSseStream } from "../lib/sse";

const STORAGE_KEY = "ivory-session-id";
const SNAPSHOT_STORAGE_KEY = "ivory-session-snapshot";
const BOOKING_STORAGE_KEY = "ivory-latest-booking";
const MESSAGES_STORAGE_KEY = "ivory-current-messages";
const HISTORY_STORAGE_KEY = "ivory-chat-history";
const CHAT_ENDPOINT = "/api/chat";
const RESET_ENDPOINT = "/api/reset";
const INITIAL_SESSION_ID = "session-pending";

const INITIAL_WELCOME_MESSAGE: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content:
    "Ask a policy question or start a quote. The assistant will keep track of the quote flow if you interrupt it.",
  streaming: false,
  kind: "info"
};

function isChatMessage(value: unknown): value is ChatMessage {
  if (!value || typeof value !== "object") {
    return false;
  }

  const record = value as Record<string, unknown>;
  return (
    typeof record.id === "string" &&
    typeof record.role === "string" &&
    typeof record.content === "string"
  );
}

function isSessionSnapshot(value: unknown): value is SessionSnapshot {
  return !!value && typeof value === "object";
}

function isBookingResult(value: unknown): value is BookingResult {
  return !!value && typeof value === "object";
}

function normalizeMessages(value: unknown): ChatMessage[] {
  if (!Array.isArray(value)) {
    return [INITIAL_WELCOME_MESSAGE];
  }

  const next = value.filter(isChatMessage).map((message) => ({
    ...message,
    streaming: false
  }));

  return next.length ? next : [INITIAL_WELCOME_MESSAGE];
}

function normalizeSavedSessions(value: unknown): SavedChatSession[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter((entry): entry is SavedChatSession => {
      if (!entry || typeof entry !== "object") {
        return false;
      }

      const record = entry as Record<string, unknown>;
      return (
        typeof record.sessionId === "string" &&
        typeof record.label === "string" &&
        typeof record.preview === "string" &&
        typeof record.updatedAt === "string" &&
        Array.isArray(record.messages)
      );
    })
    .map((entry) => ({
      ...entry,
      messages: normalizeMessages(entry.messages),
      sessionSnapshot: isSessionSnapshot(entry.sessionSnapshot)
        ? entry.sessionSnapshot
        : null,
      bookingResult: isBookingResult(entry.bookingResult) ? entry.bookingResult : null
    }));
}

function hasMeaningfulConversation(messages: ChatMessage[]): boolean {
  return messages.some(
    (message) =>
      message.id !== INITIAL_WELCOME_MESSAGE.id && message.content.trim().length > 0
  );
}

function createSessionId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `session_${Math.random().toString(36).slice(2, 10)}`;
}

function getStoredSessionId(): string {
  if (typeof window === "undefined") {
    return INITIAL_SESSION_ID;
  }

  const existing = window.localStorage.getItem(STORAGE_KEY);
  if (existing) {
    return existing;
  }

  const next = createSessionId();
  window.localStorage.setItem(STORAGE_KEY, next);
  return next;
}

function extractText(payload: unknown): string | null {
  if (typeof payload === "string") {
    return payload;
  }

  if (!payload || typeof payload !== "object") {
    return null;
  }

  const record = payload as Record<string, unknown>;
  for (const key of ["message", "content", "text", "assistant_message"]) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }

  return null;
}

function looksLikeBookingResult(value: Record<string, unknown>): value is BookingResult {
  return (
    "premium" in value ||
    "annual_premium" in value ||
    "product_type" in value ||
    "coverage_level" in value ||
    "term_years" in value
  );
}

function extractBookingResult(payload: unknown): BookingResult | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const record = payload as Record<string, unknown>;
  const direct =
    record.booking_result ?? record.bookingResult;

  if (direct && typeof direct === "object") {
    return direct as BookingResult;
  }

  if (looksLikeBookingResult(record)) {
    return record as BookingResult;
  }

  return null;
}

function summarizeBookingResult(result: BookingResult): string {
  const premium =
    typeof result.premium === "number"
      ? result.premium
      : typeof result.annual_premium === "number"
        ? result.annual_premium
        : null;
  const currency = result.currency || "USD";
  const amount =
    premium === null
      ? "Booking calculated"
      : new Intl.NumberFormat("en-US", {
          style: "currency",
          currency
        }).format(premium);
  const product = result.product_type
    ? String(result.product_type)
    : "service";
  const coverage = result.coverage_level ? ` ${String(result.coverage_level)}` : "";

  return `${product}${coverage} booking ready. ${amount}.`;
}

function makeAssistantMessage(
  id: string,
  content = "",
  bookingResult: BookingResult | null = null
): ChatMessage {
  return {
    id,
    role: "assistant",
    content,
    streaming: true,
    bookingResult
  };
}

function toMessageText(data: unknown, fallback: string): string {
  const text = extractText(data);
  if (text) {
    return text;
  }

  const booking = extractBookingResult(data);
  if (booking) {
    return summarizeBookingResult(booking);
  }

  return fallback;
}

function normalizeErrorMessage(data: unknown): string {
  const text = extractText(data);
  if (text) {
    return text;
  }

  if (data && typeof data === "object") {
    const record = data as Record<string, unknown>;
    for (const key of ["error", "detail", "message"]) {
      const value = record[key];
      if (typeof value === "string" && value.trim()) {
        return value;
      }
    }
  }

  return "The assistant returned an error event.";
}

function extractSessionSnapshot(payload: unknown): SessionSnapshot | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const record = payload as Record<string, unknown>;
  const session = record.session;
  if (!session || typeof session !== "object") {
    return null;
  }

  return session as SessionSnapshot;
}

function readJsonStorage<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") {
    return fallback;
  }

  const raw = window.localStorage.getItem(key);
  if (!raw) {
    return fallback;
  }

  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function createWelcomeMessage(content: string): ChatMessage[] {
  return [
    {
      ...INITIAL_WELCOME_MESSAGE,
      id: "welcome",
      content
    }
  ];
}

function createSessionPreview(messages: ChatMessage[]): string {
  const firstUserMessage = messages.find(
    (message) => message.role === "user" && message.content.trim()
  );

  if (firstUserMessage) {
    return firstUserMessage.content.trim().slice(0, 72);
  }

  const firstAssistantMessage = messages.find((message) => message.content.trim());
  if (firstAssistantMessage) {
    return firstAssistantMessage.content.trim().slice(0, 72);
  }

  return "New conversation";
}

function sanitizeMessages(messages: ChatMessage[]): ChatMessage[] {
  return messages.map((message) => ({
    ...message,
    streaming: false
  }));
}

function buildSavedSession(
  sessionId: string,
  messages: ChatMessage[],
  sessionSnapshot: SessionSnapshot | null,
  bookingResult: BookingResult | null
): SavedChatSession {
  return {
    sessionId,
    label: sessionId.slice(0, 8),
    preview: createSessionPreview(messages),
    updatedAt: new Date().toISOString(),
    messages: sanitizeMessages(messages),
    sessionSnapshot,
    bookingResult
  };
}

export function useChat() {
  const [sessionId, setSessionId] = useState(INITIAL_SESSION_ID);
  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_WELCOME_MESSAGE]);
  const [savedSessions, setSavedSessions] = useState<SavedChatSession[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [bookingResult, setBookingResult] = useState<BookingResult | null>(null);
  const [sessionSnapshot, setSessionSnapshot] = useState<SessionSnapshot | null>(null);
  const [statusText, setStatusText] = useState("Ready");
  const [hasHydrated, setHasHydrated] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const activeAssistantIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const storedSessionId = getStoredSessionId();
    setSessionId((current) =>
      current === storedSessionId ? current : storedSessionId
    );
    const storedSnapshot = readJsonStorage<unknown>(SNAPSHOT_STORAGE_KEY, null);
    const storedBooking = readJsonStorage<unknown>(BOOKING_STORAGE_KEY, null);
    const storedMessages = readJsonStorage<unknown>(MESSAGES_STORAGE_KEY, [
      INITIAL_WELCOME_MESSAGE
    ]);
    const storedHistory = readJsonStorage<unknown>(HISTORY_STORAGE_KEY, []);

    setSessionSnapshot(isSessionSnapshot(storedSnapshot) ? storedSnapshot : null);
    setBookingResult(isBookingResult(storedBooking) ? storedBooking : null);
    setMessages(normalizeMessages(storedMessages));
    setSavedSessions(normalizeSavedSessions(storedHistory));
    setHasHydrated(true);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined" || sessionId === INITIAL_SESSION_ID) {
      return;
    }

    window.localStorage.setItem(STORAGE_KEY, sessionId);
  }, [sessionId]);

  useEffect(() => {
    if (typeof window === "undefined" || !hasHydrated) {
      return;
    }

    window.localStorage.setItem(
      MESSAGES_STORAGE_KEY,
      JSON.stringify(sanitizeMessages(messages))
    );

    if (sessionSnapshot) {
      window.localStorage.setItem(
        SNAPSHOT_STORAGE_KEY,
        JSON.stringify(sessionSnapshot)
      );
    } else {
      window.localStorage.removeItem(SNAPSHOT_STORAGE_KEY);
    }

    if (bookingResult) {
      window.localStorage.setItem(BOOKING_STORAGE_KEY, JSON.stringify(bookingResult));
    } else {
      window.localStorage.removeItem(BOOKING_STORAGE_KEY);
    }

    if (sessionId === INITIAL_SESSION_ID) {
      return;
    }

    const existingHistory = normalizeSavedSessions(
      readJsonStorage<unknown>(HISTORY_STORAGE_KEY, [])
    );

    const nextHistory = bookingResult && hasMeaningfulConversation(messages)
      ? [
          buildSavedSession(sessionId, messages, sessionSnapshot, bookingResult),
          ...existingHistory.filter((entry) => entry.sessionId !== sessionId)
        ].slice(0, 20)
      : existingHistory.filter((entry) => entry.sessionId !== sessionId).slice(0, 20);

    window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(nextHistory));
    setSavedSessions(nextHistory);
  }, [hasHydrated, messages, bookingResult, sessionId, sessionSnapshot]);

  const stopGeneration = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    activeAssistantIdRef.current = null;
    setIsSending(false);
    setStatusText("Generation stopped");
  }, []);

  const patchAssistantMessage = useCallback(
    (assistantId: string, updater: (message: ChatMessage) => ChatMessage) => {
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId ? updater(message) : message
        )
      );
    },
    []
  );

  const sendMessage = useCallback(
    async (input: string) => {
      const trimmed = input.trim();
      if (!trimmed || isSending || isResetting) {
        return;
      }

      setError(null);
      setStatusText("Sending");
      setIsSending(true);

      const userMessage: ChatMessage = {
        id: createSessionId(),
        role: "user",
        content: trimmed,
        streaming: false
      };
      const assistantId = createSessionId();
      activeAssistantIdRef.current = assistantId;

      setMessages((current) => [
        ...current,
        userMessage,
        makeAssistantMessage(assistantId)
      ]);

      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const response = await fetch(CHAT_ENDPOINT, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream"
          },
          body: JSON.stringify({
            message: trimmed,
            session_id: sessionId
          }),
          signal: controller.signal
        });

        if (!response.ok) {
          const bodyText = await response.text().catch(() => "");
          throw new Error(
            bodyText.trim() ||
              `Failed to send message (${response.status} ${response.statusText})`
          );
        }

        if (!response.body) {
          throw new Error("The server did not return a streaming body.");
        }

        for await (const event of parseSseStream(response.body)) {
          if (controller.signal.aborted) {
            break;
          }

          const payload = parseSseData(event.data);

          if (event.event === "token") {
            const token = extractText(payload) ?? String(payload ?? "");
            patchAssistantMessage(assistantId, (message) => ({
              ...message,
              content: `${message.content}${token}`,
              streaming: true
            }));
            continue;
          }

          if (event.event === "message_complete") {
            const finalText = toMessageText(payload, "");
            const result = extractBookingResult(payload);
            const session = extractSessionSnapshot(payload);
            if (result) {
              setBookingResult(result);
            }
            if (session) {
              setSessionSnapshot(session);
            }

            patchAssistantMessage(assistantId, (message) => ({
              ...message,
              content: finalText || message.content,
              streaming: false,
              bookingResult: result ?? message.bookingResult ?? null
            }));

            setStatusText("Ready");
            continue;
          }

          if (event.event === "error") {
            const message = normalizeErrorMessage(payload);
            setError(message);
            patchAssistantMessage(assistantId, (current) => ({
              ...current,
              content: current.content || message,
              streaming: false,
              kind: "error"
            }));
            setStatusText("Error");
            continue;
          }

          if (event.event === "state") {
            const stateText = extractText(payload);
            if (stateText) {
              setStatusText(stateText);
            }
          }
        }
      } catch (err) {
        if (controller.signal.aborted) {
          return;
        }

        const message =
          err instanceof Error ? err.message : "A network error occurred.";
        setError(message);
        patchAssistantMessage(assistantId, (current) => ({
          ...current,
          content: current.content || message,
          streaming: false,
          kind: "error"
        }));
        setStatusText("Error");
      } finally {
        if (activeAssistantIdRef.current === assistantId) {
          activeAssistantIdRef.current = null;
        }

        if (abortRef.current === controller) {
          abortRef.current = null;
        }

        setIsSending(false);
      }
    },
    [isResetting, isSending, patchAssistantMessage, sessionId]
  );

  const resetSession = useCallback(async () => {
    if (isResetting) {
      return;
    }

    setIsResetting(true);
    setError(null);
    stopGeneration();
    setStatusText("Resetting");

    try {
      const response = await fetch(RESET_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ session_id: sessionId })
      });

      if (!response.ok) {
        const bodyText = await response.text().catch(() => "");
        throw new Error(
          bodyText.trim() ||
            `Failed to reset session (${response.status} ${response.statusText})`
        );
      }
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "The session could not be reset.";
      setError(message);
    } finally {
      setMessages(
        createWelcomeMessage(
          "The session has been reset. Start a new quote or ask a product question."
        )
      );
      setBookingResult(null);
      setSessionSnapshot({
        session_id: sessionId,
        mode: "conversational",
        intent: "question",
        intake_step: "identify",
        service_type: null,
        current_field: null,
        has_booking_result: false
      });
      setIsResetting(false);
      setStatusText("Ready");
    }
  }, [isResetting, sessionId, stopGeneration]);

  const createNewSession = useCallback(() => {
    stopGeneration();
    const next = createSessionId();
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, next);
    }
    setSessionId(next);
    setMessages(
      createWelcomeMessage(
        "New session started. Ask a question or begin a fresh quote flow."
      )
    );
    setBookingResult(null);
    setSessionSnapshot({
      session_id: next,
      mode: "conversational",
      intent: "question",
      intake_step: "identify",
      service_type: null,
      current_field: null,
      has_booking_result: false
    });
    setError(null);
    setStatusText("Ready");
  }, [stopGeneration]);

  const restoreSession = useCallback((saved: SavedChatSession) => {
    stopGeneration();
    setSessionId(saved.sessionId);
    setMessages(normalizeMessages(saved.messages));
    setBookingResult(isBookingResult(saved.bookingResult) ? saved.bookingResult : null);
    setSessionSnapshot(
      isSessionSnapshot(saved.sessionSnapshot) ? saved.sessionSnapshot : null
    );
    setError(null);
    setStatusText("Ready");
  }, [stopGeneration]);

  const sessionLabel = useMemo(() => {
    return sessionId === INITIAL_SESSION_ID ? "pending" : sessionId.slice(0, 8);
  }, [sessionId]);

  return {
    sessionId,
    sessionLabel,
    messages,
    bookingResult,
    sessionSnapshot,
    savedSessions,
    error,
    statusText,
    isSending,
    isResetting,
    sendMessage,
    resetSession,
    createNewSession,
    restoreSession,
    stopGeneration
  };
}
