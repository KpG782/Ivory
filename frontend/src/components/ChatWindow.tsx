"use client";

import { useEffect, useRef } from "react";
import type { ChatMessage } from "../types";
import { IvoryLogo } from "./IvoryLogo";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";

const STARTER_PROMPTS = [
  {
    title: "Start an auto quote",
    hint: "Five quick details, instant premium",
    prompt: "I want a quote for auto insurance"
  },
  {
    title: "What does comprehensive include?",
    hint: "Answers from the policy knowledge base",
    prompt: "What does comprehensive coverage include?"
  },
  {
    title: "Home insurance quote",
    hint: "Coverage for your property in minutes",
    prompt: "I want a home insurance quote"
  },
  {
    title: "Compare pricing tiers",
    hint: "Basic, standard, and premium side by side",
    prompt: "Compare the pricing tiers"
  }
];

const QUICK_REPLIES = [
  { label: "Accept", message: "accept" },
  { label: "Adjust details", message: "adjust" },
  { label: "Start over", message: "restart" }
];

interface ChatWindowProps {
  messages: ChatMessage[];
  draft: string;
  error: string | null;
  isSending: boolean;
  isResetting: boolean;
  hasQuoteResult: boolean;
  onDraftChange: (value: string) => void;
  onSend: () => void;
  onStop: () => void;
  onQuickPrompt: (prompt: string) => void;
}

export function ChatWindow({
  messages,
  draft,
  error,
  isSending,
  isResetting,
  hasQuoteResult,
  onDraftChange,
  onSend,
  onStop,
  onQuickPrompt
}: ChatWindowProps) {
  const listRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const showWelcome = messages.length <= 1 && !isSending;

  useEffect(() => {
    const node = listRef.current;
    if (!node) {
      return;
    }

    node.scrollTop = node.scrollHeight;
  }, [messages]);

  // Auto-grow the composer up to its max-h cap, shrink back when cleared.
  useEffect(() => {
    const node = textareaRef.current;
    if (!node) {
      return;
    }

    node.style.height = "auto";
    node.style.height = `${node.scrollHeight}px`;
  }, [draft]);

  return (
    <section className="flex h-full min-h-0 flex-col">
      {showWelcome ? (
        <div className="flex flex-1 flex-col items-center justify-center overflow-y-auto px-4 py-8">
          <IvoryLogo className="h-14 w-14" />
          <h1 className="mt-5 text-center font-[family-name:var(--font-display)] text-3xl text-ink sm:text-4xl">
            How can we help today?
          </h1>
          <p className="mt-2 max-w-md text-center text-[15px] leading-6 text-muted">
            Ask a policy question, or start a quote — Ivory keeps your place if
            you get interrupted.
          </p>
          <div className="mt-8 grid w-full max-w-2xl gap-3 sm:grid-cols-2">
            {STARTER_PROMPTS.map((starter) => (
              <button
                key={starter.title}
                type="button"
                className="rounded-xl border border-line bg-white p-4 text-left transition-shadow hover:shadow-md"
                onClick={() => onQuickPrompt(starter.prompt)}
              >
                <p className="text-sm font-semibold text-ink">{starter.title}</p>
                <p className="mt-1 text-[13px] leading-5 text-muted">
                  {starter.hint}
                </p>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto" ref={listRef}>
          <div className="mx-auto w-full max-w-3xl space-y-6 px-4 py-6">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {isSending && messages[messages.length - 1]?.content ? (
              <div
                role="status"
                aria-live="polite"
                className="ui-fade-in flex items-center gap-3 text-sm text-muted"
              >
                <IvoryLogo className="h-7 w-7 shrink-0" />
                <TypingIndicator />
              </div>
            ) : null}
          </div>
        </div>
      )}

      {error ? (
        <div
          role="alert"
          className="mx-auto mb-2 w-full max-w-3xl rounded-xl border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-900"
        >
          {error}
        </div>
      ) : null}

      <form
        className="mx-auto w-full max-w-3xl px-4 pb-5"
        onSubmit={(event) => {
          event.preventDefault();
          onSend();
        }}
      >
        {hasQuoteResult && !isSending && !showWelcome ? (
          <div className="mb-2 flex flex-wrap gap-2">
            {QUICK_REPLIES.map((reply) => (
              <button
                key={reply.message}
                type="button"
                className="rounded-full border border-line bg-white px-3 py-1.5 text-[13px] font-medium text-muted transition-colors hover:border-teal hover:text-teal"
                onClick={() => onQuickPrompt(reply.message)}
              >
                {reply.label}
              </button>
            ))}
          </div>
        ) : null}

        <div className="flex items-end gap-2 rounded-[28px] border border-line bg-white px-4 py-2.5 shadow-sm transition focus-within:border-teal focus-within:ring-4 focus-within:ring-teal/10">
          <label className="sr-only" htmlFor="message-input">
            Message Ivory
          </label>
          <textarea
            id="message-input"
            ref={textareaRef}
            rows={1}
            className="max-h-40 flex-1 resize-none bg-transparent py-1.5 text-base text-ink outline-none placeholder:text-muted/60"
            value={draft}
            onChange={(event) => onDraftChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                onSend();
              }
            }}
            placeholder="Message Ivory…"
          />
          {isSending ? (
            <button
              type="button"
              onClick={onStop}
              aria-label="Stop generating"
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-ink sm:h-9 sm:w-9 text-white transition-colors hover:bg-black"
            >
              <svg className="h-3 w-3" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
                <rect width="12" height="12" rx="2" />
              </svg>
            </button>
          ) : (
            <button
              type="submit"
              aria-label="Send message"
              aria-busy={isSending}
              disabled={!draft.trim() || isResetting}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-teal sm:h-9 sm:w-9 text-white transition-colors hover:bg-teal-hover disabled:cursor-not-allowed disabled:bg-line disabled:text-muted"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 10l7-7m0 0l7 7m-7-7v18" />
              </svg>
            </button>
          )}
        </div>
        <p className="mt-2 text-center text-xs text-muted/70">
          Ivory is an AI assistant — quotes are estimates, not final offers.
        </p>
      </form>
    </section>
  );
}
