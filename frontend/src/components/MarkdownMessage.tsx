"use client";

import { Fragment, type ReactNode } from "react";

/**
 * Minimal, dependency-free Markdown renderer for assistant messages.
 *
 * The backend emits simple prose: short paragraphs, the occasional **bold**
 * span, `inline code`, and `-`/`*`/`1.` lists. Rather than pull in a heavy
 * Markdown dependency (and its sanitisation surface), we render a small,
 * known subset directly into React nodes — which is XSS-safe by construction
 * because nothing is ever set as raw HTML.
 *
 * Supported: blank-line paragraphs, single newlines (as <br/>), unordered and
 * ordered lists, **bold**, and `inline code`.
 */

const INLINE_PATTERN = /(\*\*([^*]+)\*\*|`([^`]+)`)/g;

function renderInline(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let key = 0;
  let match: RegExpExecArray | null;

  INLINE_PATTERN.lastIndex = 0;
  while ((match = INLINE_PATTERN.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }
    if (match[2] !== undefined) {
      nodes.push(
        <strong key={`b${key++}`} className="font-semibold text-slate-900">
          {match[2]}
        </strong>,
      );
    } else if (match[3] !== undefined) {
      nodes.push(
        <code
          key={`c${key++}`}
          className="rounded bg-black/[0.06] px-1 py-0.5 font-mono text-[0.85em]"
        >
          {match[3]}
        </code>,
      );
    }
    lastIndex = INLINE_PATTERN.lastIndex;
  }
  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }
  return nodes;
}

const BULLET = /^\s*[-*]\s+/;
const NUMBERED = /^\s*\d+\.\s+/;

export function MarkdownMessage({ content }: { content: string }) {
  const blocks = content.split(/\n{2,}/);

  return (
    <div className="space-y-3">
      {blocks.map((block, blockIndex) => {
        const lines = block.split("\n").filter((line) => line.length > 0);
        if (lines.length === 0) {
          return null;
        }

        if (lines.every((line) => BULLET.test(line))) {
          return (
            <ul key={blockIndex} className="list-disc space-y-1 pl-5 marker:text-slate-400">
              {lines.map((line, i) => (
                <li key={i}>{renderInline(line.replace(BULLET, ""))}</li>
              ))}
            </ul>
          );
        }

        if (lines.every((line) => NUMBERED.test(line))) {
          return (
            <ol key={blockIndex} className="list-decimal space-y-1 pl-5 marker:text-slate-400">
              {lines.map((line, i) => (
                <li key={i}>{renderInline(line.replace(NUMBERED, ""))}</li>
              ))}
            </ol>
          );
        }

        return (
          <p key={blockIndex}>
            {lines.map((line, i) => (
              <Fragment key={i}>
                {i > 0 ? <br /> : null}
                {renderInline(line)}
              </Fragment>
            ))}
          </p>
        );
      })}
    </div>
  );
}
