"use client";

import { memo } from "react";
import type { ChatMessage } from "../types";
import { IvoryLogo } from "./IvoryLogo";
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
  if (message.role === "assistant") {
    return (
      <article className="ui-rise-in flex gap-3">
        <IvoryLogo className="mt-0.5 h-7 w-7 shrink-0" />
        <div className="min-w-0 flex-1">
          <div
            className={`break-words text-[15px] leading-7 text-ink ${
              message.kind === "error"
                ? "rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-rose-950"
                : ""
            }`}
            style={{ overflowWrap: "anywhere" }}
            aria-live={message.streaming ? "polite" : undefined}
          >
            <MessageBody message={message} />
          </div>
          {message.bookingResult ? (
            <div className="mt-3 max-w-md">
              <QuoteCard quote={message.bookingResult} />
            </div>
          ) : null}
        </div>
      </article>
    );
  }

  return (
    <article className="ui-rise-in flex justify-end">
      <div
        className="max-w-[75%] break-words rounded-2xl rounded-br-md bg-teal px-4 py-2.5 text-[15px] leading-6 text-white"
        style={{ overflowWrap: "anywhere" }}
      >
        <MessageBody message={message} />
      </div>
    </article>
  );
}

/**
 * Memoized so streaming a token only re-renders the live message, not the
 * entire message list.
 */
export const MessageBubble = memo(MessageBubbleComponent);
