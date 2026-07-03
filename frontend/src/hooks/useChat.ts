"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  ChatMessage,
  SavedChatSession,
  SessionSnapshot,
  VisitEstimate
} from "../types";
import { parseSseData, parseSseStream } from "../lib/sse";

const STORAGE_KEY = "ivory-session-id";
const SNAPSHOT_STORAGE_KEY = "ivory-session-snapshot";
const ESTIMATE_STORAGE_KEY = "ivory-latest-estimate";
const MESSAGES_STORAGE_KEY = "ivory-current-messages";
const HISTORY_STORAGE_KEY = "ivory-chat-history";
const CHAT_ENDPOINT = "/api/chat";
const RESET_ENDPOINT = "/api/reset";
const INITIAL_SESSION_ID = "session-pending";

const INITIAL_WELCOME_MESSAGE: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content:
    "Ask a dental question or set up a visit. The assistant will keep track of your intake if you interrupt it.",
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

function isVisitEstimate(value: unknown): value is VisitEstimate {
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
      visitEstimate: isVisitEstimate(entry.visitEstimate)
        ? entry.visitEstimate
        : null
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

function looksLikeVisitEstimate(value: Record<string, unknown>): value is VisitEstimate {
  return (
    "estimate_low" in value ||
    "estimate_high" in value ||
    "service_type" in value
  );
}

function extractVisitEstimate(payload: unknown): VisitEstimate | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const record = payload as Record<string, unknown>;
  const direct = record.visit_estimate ?? record.visitEstimate ?? record.result;

  if (direct && typeof direct === "object") {
    return direct as VisitEstimate;
  }

  if (looksLikeVisitEstimate(record)) {
    return record as VisitEstimate;
  }

  return null;
}

function summarizeVisitEstimate(estimate: VisitEstimate): string {
  const low = typeof estimate.estimate_low === "number" ? estimate.estimate_low : null;
  const high =
    typeof estimate.estimate_high === "number" ? estimate.estimate_high : null;
  const currency = estimate.currency || "USD";
  const formatter = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency
  });
  const amount =
    low === null || high === null
      ? "Estimate calculated"
      : `${formatter.format(low)}–${formatter.format(high)}`;
  const service = estimate.service_type
    ? String(estimate.service_type)
    : "visit";

  return `${service} estimate ready. ${amount}.`;
}

function makeAssistantMessage(
  id: string,
  content = "",
  visitEstimate: VisitEstimate | null = null
): ChatMessage {
  return {
    id,
    role: "assistant",
    content,
    streaming: true,
    visitEstimate
  };
}

function toMessageText(data: unknown, fallback: string): string {
  const text = extractText(data);
  if (text) {
    return text;
  }

  const estimate = extractVisitEstimate(data);
  if (estimate) {
    return summarizeVisitEstimate(estimate);
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
  visitEstimate: VisitEstimate | null
): SavedChatSession {
  return {
    sessionId,
    label: sessionId.slice(0, 8),
    preview: createSessionPreview(messages),
    updatedAt: new Date().toISOString(),
    messages: sanitizeMessages(messages),
    sessionSnapshot,
    visitEstimate
  };
}

export function useChat() {
  const [sessionId, setSessionId] = useState(INITIAL_SESSION_ID);
  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_WELCOME_MESSAGE]);
  const [savedSessions, setSavedSessions] = useState<SavedChatSession[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [visitEstimate, setVisitEstimate] = useState<VisitEstimate | null>(null);
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
    const storedEstimate = readJsonStorage<unknown>(ESTIMATE_STORAGE_KEY, null);
    const storedMessages = readJsonStorage<unknown>(MESSAGES_STORAGE_KEY, [
      INITIAL_WELCOME_MESSAGE
    ]);
    const storedHistory = readJsonStorage<unknown>(HISTORY_STORAGE_KEY, []);

    setSessionSnapshot(isSessionSnapshot(storedSnapshot) ? storedSnapshot : null);
    setVisitEstimate(isVisitEstimate(storedEstimate) ? storedEstimate : null);
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

    if (visitEstimate) {
      window.localStorage.setItem(
        ESTIMATE_STORAGE_KEY,
        JSON.stringify(visitEstimate)
      );
    } else {
      window.localStorage.removeItem(ESTIMATE_STORAGE_KEY);
    }

    if (sessionId === INITIAL_SESSION_ID) {
      return;
    }

    const existingHistory = normalizeSavedSessions(
      readJsonStorage<unknown>(HISTORY_STORAGE_KEY, [])
    );

    const nextHistory = visitEstimate && hasMeaningfulConversation(messages)
      ? [
          buildSavedSession(sessionId, messages, sessionSnapshot, visitEstimate),
          ...existingHistory.filter((entry) => entry.sessionId !== sessionId)
        ].slice(0, 20)
      : existingHistory.filter((entry) => entry.sessionId !== sessionId).slice(0, 20);

    window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(nextHistory));
    setSavedSessions(nextHistory);
  }, [hasHydrated, messages, sessionId, sessionSnapshot, visitEstimate]);

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
            const result = extractVisitEstimate(payload);
            const session = extractSessionSnapshot(payload);
            if (result) {
              setVisitEstimate(result);
            }
            if (session) {
              setSessionSnapshot(session);
            }

            patchAssistantMessage(assistantId, (message) => ({
              ...message,
              content: finalText || message.content,
              streaming: false,
              visitEstimate: result ?? message.visitEstimate ?? null
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
          "The session has been reset. Set up a new visit or ask a dental question."
        )
      );
      setVisitEstimate(null);
      setSessionSnapshot({
        session_id: sessionId,
        mode: "conversational",
        intent: "question",
        intake_step: "identify",
        service_type: null,
        current_field: null,
        has_visit_estimate: false
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
        "New session started. Ask a question or set up a fresh visit."
      )
    );
    setVisitEstimate(null);
    setSessionSnapshot({
      session_id: next,
      mode: "conversational",
      intent: "question",
      intake_step: "identify",
      service_type: null,
      current_field: null,
      has_visit_estimate: false
    });
    setError(null);
    setStatusText("Ready");
  }, [stopGeneration]);

  const restoreSession = useCallback((saved: SavedChatSession) => {
    stopGeneration();
    setSessionId(saved.sessionId);
    setMessages(normalizeMessages(saved.messages));
    setVisitEstimate(
      isVisitEstimate(saved.visitEstimate) ? saved.visitEstimate : null
    );
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
    visitEstimate,
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
