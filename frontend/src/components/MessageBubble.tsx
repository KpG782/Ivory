"use client";

import { memo } from "react";
import type { ChatMessage } from "../types";
import { MarkdownMessage } from "./MarkdownMessage";
import { QuoteCard } from "./QuoteCard";
import { TypingIndicator } from "./TypingIndicator";

function MessageBody({ message }: { message: ChatMessage }) {
  if (!message.content.trim() && message.streaming) {
    return <TypingIndicator />;
  }

  // User text is shown verbatim (preserve their line breaks); assistant
  // answers are rendered as lightweight Markdown.
  if (message.role === "assistant") {
    return <MarkdownMessage content={message.content} />;
  }

  return <p className="whitespace-pre-wrap">{message.content}</p>;
}

function MessageBubbleComponent({ message }: { message: ChatMessage }) {
  const bubbleClassName =
    message.role === "user"
      ? "ml-auto w-full max-w-[92%] rounded-[1.4rem] bg-[#1f1f1f] px-4 py-3 text-white shadow-[0_10px_30px_rgba(15,23,42,0.14)] sm:max-w-[70%]"
      : "mr-auto w-full max-w-[94%] rounded-[1.6rem] border border-black/8 bg-white/90 px-4 py-4 shadow-[0_10px_30px_rgba(15,23,42,0.06)] backdrop-blur sm:max-w-[78%]";

  const stateClassName =
    message.kind === "error"
      ? "border-rose-200 bg-rose-50 text-rose-950"
      : message.kind === "info"
        ? "border-[#d7cfb9] bg-[#fbf7ec]"
        : "";

  return (
    <article className={`ui-rise-in ${bubbleClassName} ${stateClassName}`.trim()}>
      <div
        className={`mb-2 flex flex-wrap items-center justify-between gap-3 text-[11px] uppercase tracking-[0.14em] ${
          message.role === "user" ? "text-white/70" : "text-slate-500"
        }`}
      >
        <span>{message.role === "user" ? "You" : "ShieldBase"}</span>
        {message.streaming ? (
          <span className="flex items-center gap-1 text-cyan-500" role="status" aria-live="polite">
            <span className="ui-soft-pulse inline-block h-1.5 w-1.5 rounded-full bg-cyan-500" />
            Live
          </span>
        ) : null}
      </div>
      <div
        className={`break-words text-sm leading-6 sm:text-[0.95rem] ${
          message.role === "user" ? "text-white" : "text-slate-800"
        }`}
        style={{ overflowWrap: "anywhere" }}
      >
        <MessageBody message={message} />
      </div>
      {message.quoteResult ? (
        <div className="mt-4">
          <QuoteCard quote={message.quoteResult} variant="embedded" />
        </div>
      ) : null}
    </article>
  );
}

/**
 * Memoized so streaming a token only re-renders the live bubble, not the
 * entire message list.
 */
export const MessageBubble = memo(MessageBubbleComponent);
