"use client";

import { useEffect, useRef } from "react";
import type { ChatMessage, QuoteResult } from "../types";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";

const QUICK_PROMPTS = [
  "What does comprehensive coverage include?",
  "I want a quote for auto insurance",
  "I want a home insurance quote"
];

interface ChatWindowProps {
  messages: ChatMessage[];
  draft: string;
  error: string | null;
  isSending: boolean;
  isResetting: boolean;
  sessionLabel: string;
  quoteResult: QuoteResult | null;
  statusText: string;
  onDraftChange: (value: string) => void;
  onSend: () => void;
  onReset: () => void;
  onNewSession: () => void;
  onStop: () => void;
  onQuickPrompt: (prompt: string) => void;
}

export function ChatWindow({
  messages,
  draft,
  error,
  isSending,
  isResetting,
  sessionLabel,
  quoteResult,
  statusText,
  onDraftChange,
  onSend,
  onReset,
  onNewSession,
  onStop,
  onQuickPrompt
}: ChatWindowProps) {
  const listRef = useRef<HTMLDivElement | null>(null);
  const showQuickPrompts = messages.length <= 1;

  useEffect(() => {
    const node = listRef.current;
    if (!node) {
      return;
    }

    node.scrollTop = node.scrollHeight;
  }, [messages, quoteResult]);

  return (
    <section className="ui-rise-in flex min-h-[70svh] min-w-0 flex-col overflow-hidden rounded-[1.75rem] border border-black/8 bg-[var(--card-background)] p-3 shadow-[var(--shadow-panel)] backdrop-blur sm:min-h-[calc(100vh-8rem)] sm:p-4">
      <header className="flex flex-col gap-3 border-b border-black/8 px-1 pb-4 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
            Conversation
          </p>
          <p className="mt-1 text-sm text-slate-500">Live conversation with Ivory</p>
        </div>
        <div className="flex flex-wrap gap-2 sm:justify-end">
          <button
            type="button"
            className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
            onClick={onNewSession}
            disabled={isSending || isResetting}
          >
            New
          </button>
          <button
            type="button"
            className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
            onClick={onReset}
            disabled={isSending || isResetting}
          >
            {isResetting ? "Resetting" : "Reset"}
          </button>
        </div>
      </header>

      {showQuickPrompts ? (
        <div className="mt-4 flex flex-wrap gap-2" aria-label="Quick prompts">
          {QUICK_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              className="ui-hover-lift w-full rounded-2xl border border-slate-200 bg-white px-3 py-2 text-left text-xs text-slate-600 transition hover:border-[#b9ab86] hover:bg-[#faf7ee] hover:text-slate-900 sm:w-auto sm:rounded-full"
              onClick={() => onQuickPrompt(prompt)}
            >
              {prompt}
            </button>
          ))}
        </div>
      ) : null}

      <div className="mt-4 min-h-0 flex-1 overflow-auto px-0 sm:px-1" ref={listRef}>
        <div className="mx-auto grid w-full max-w-3xl gap-4 pb-4 pt-1 sm:pb-6">
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
          {isSending ? (
            <div
              role="status"
              aria-live="polite"
              className="ui-scale-in ui-sheen mr-auto flex w-full max-w-[92%] items-center gap-3 rounded-[1.4rem] border border-black/8 bg-white/90 px-4 py-3 text-sm text-slate-600 shadow-[0_10px_30px_rgba(15,23,42,0.06)] sm:max-w-[78%]">
              <TypingIndicator />
              <span>Generating response...</span>
            </div>
          ) : null}
        </div>
      </div>

      {error ? (
        <div
          role="alert"
          className="mx-auto mt-2 w-full max-w-3xl rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900">
          {error}
        </div>
      ) : null}

      <form
        className="ui-scale-in mx-auto mt-3 grid w-full max-w-3xl min-w-0 gap-3 rounded-[1.5rem] border border-black/8 bg-white/90 p-3 shadow-[0_10px_24px_rgba(15,23,42,0.05)] sm:mt-3"
        onSubmit={(event) => {
          event.preventDefault();
          onSend();
        }}
      >
        <label className="sr-only" htmlFor="message-input">
          Message
        </label>
        <textarea
          id="message-input"
          className="min-h-[96px] w-full resize-none rounded-[1.15rem] border border-slate-200 bg-[#fcfcfa] px-4 py-3 text-slate-900 outline-none transition focus:border-[#bca46b] focus:ring-4 focus:ring-[#efe4c8] sm:min-h-19"
          value={draft}
          onChange={(event) => onDraftChange(event.target.value)}
          placeholder="Ask a question or provide quote details..."
          rows={3}
        />
        <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
          <p className="max-w-full text-xs leading-5 text-slate-500 sm:max-w-[18rem]">
            Keep messages short when entering quote details.
          </p>
          <div className="flex w-full flex-col gap-2 sm:ml-auto sm:w-auto sm:flex-row sm:items-center">
            {isSending ? (
              <button
                type="button"
                className="ui-hover-lift w-full rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 sm:w-auto"
                onClick={onStop}
              >
                Stop
              </button>
            ) : null}
              <button
                type="submit"
                className="ui-hover-lift w-full rounded-full bg-[#1f1f1f] px-4 py-2 text-sm font-semibold text-white transition hover:bg-black disabled:cursor-not-allowed disabled:bg-slate-300 sm:w-auto"
                disabled={!draft.trim() || isResetting || isSending}
                aria-busy={isSending}
              >
                {isSending ? "Sending..." : "Send"}
            </button>
          </div>
        </div>
      </form>
    </section>
  );
}
