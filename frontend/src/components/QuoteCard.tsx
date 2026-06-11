"use client";

import { useMemo, useState } from "react";
import type { QuoteResult } from "../types";

function formatValue(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }

  if (typeof value === "number") {
    return new Intl.NumberFormat("en-US").format(value);
  }

  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }

  if (Array.isArray(value)) {
    return value.map(formatValue).join(", ");
  }

  if (value && typeof value === "object") {
    return JSON.stringify(value);
  }

  return "";
}

function formatCurrency(result: QuoteResult): string | null {
  const premium =
    typeof result.premium === "number"
      ? result.premium
      : typeof result.annual_premium === "number"
        ? result.annual_premium
        : null;

  if (premium === null) {
    return null;
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: result.currency || "USD"
  }).format(premium);
}

function sanitizeFilePart(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "quote";
}

function buildExportFileName(quote: QuoteResult, extension: string): string {
  const product = sanitizeFilePart(String(quote.product_type || "insurance"));
  const coverage = sanitizeFilePart(String(quote.coverage_level || "quote"));
  return `ivory-${product}-${coverage}.${extension}`;
}

function toPrettyJson(quote: QuoteResult): string {
  return JSON.stringify(quote, null, 2);
}

function toCsv(quote: QuoteResult): string {
  const rows = Object.entries(quote).map(([key, value]) => [
    key,
    Array.isArray(value)
      ? value.map((item) => formatValue(item)).join(", ")
      : formatValue(value)
  ]);

  const escapeCell = (cell: string) => `"${cell.replace(/"/g, "\"\"")}"`;
  const lines = [
    ["field", "value"],
    ...rows
  ].map((cells) => cells.map(escapeCell).join(","));

  return lines.join("\r\n");
}

function downloadTextFile(filename: string, content: string, type: string): void {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

interface QuoteCardProps {
  quote: QuoteResult | null;
  variant?: "spotlight" | "embedded";
}

const PRIORITY_FIELDS = [
  "coverage_level",
  "vehicle",
  "vehicle_year",
  "vehicle_make",
  "vehicle_model",
  "deductible",
  "term_years",
  "policy_type"
];

export function QuoteCard({
  quote,
  variant = "embedded"
}: QuoteCardProps) {
  const [exportStatus, setExportStatus] = useState<string | null>(null);

  const cardClassName =
    variant === "spotlight"
      ? "ui-scale-in ui-sheen rounded-[1.5rem] border border-black/8 bg-white/95 p-5 text-slate-900 shadow-[0_16px_44px_rgba(15,23,42,0.08)] backdrop-blur"
      : "ui-scale-in rounded-[1.25rem] border border-black/8 bg-[#fbfbf8] p-4 shadow-[0_8px_24px_rgba(15,23,42,0.05)]";

  const premium = quote ? formatCurrency(quote) : null;
  const summary = quote ? quote.summary || quote.product_type || "Insurance quote" : null;

  const filteredEntries = useMemo(() => {
    if (!quote) {
      return [];
    }

    return Object.entries(quote).filter(
      ([key, value]) =>
        ![
          "summary",
          "product_type",
          "premium",
          "annual_premium",
          "currency"
        ].includes(key) && value !== undefined && value !== null && value !== ""
    );
  }, [quote]);

  const entries = useMemo(() => {
    return filteredEntries
      .sort(([left], [right]) => {
        const leftIndex = PRIORITY_FIELDS.indexOf(left);
        const rightIndex = PRIORITY_FIELDS.indexOf(right);

        return (leftIndex === -1 ? 999 : leftIndex) - (rightIndex === -1 ? 999 : rightIndex);
      })
      .slice(0, variant === "spotlight" ? 6 : 4);
  }, [filteredEntries, variant]);

  async function handleCopyJson(): Promise<void> {
    if (!quote) {
      return;
    }

    const json = toPrettyJson(quote);
    try {
      await navigator.clipboard.writeText(json);
      setExportStatus("JSON copied");
    } catch {
      setExportStatus("Copy failed");
    }
  }

  function handleDownloadJson(): void {
    if (!quote) {
      return;
    }

    downloadTextFile(
      buildExportFileName(quote, "json"),
      toPrettyJson(quote),
      "application/json;charset=utf-8"
    );
    setExportStatus("JSON downloaded");
  }

  function handleDownloadCsv(): void {
    if (!quote) {
      return;
    }

    downloadTextFile(
      buildExportFileName(quote, "csv"),
      toCsv(quote),
      "text/csv;charset=utf-8"
    );
    setExportStatus("CSV downloaded");
  }

  if (!quote) {
    return (
      <section className={cardClassName}>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
          Quote summary
        </p>
        <p className="mt-3 text-sm text-slate-500">Draft quote in progress.</p>
        <div className="mt-4 rounded-xl border border-dashed border-slate-300 px-3 py-4 text-center text-sm text-slate-400">
          Waiting for premium
        </div>
      </section>
    );
  }

  return (
    <section className={`${cardClassName} min-w-0`}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
            Quote summary
          </p>
          <h2 className="mt-2 break-words text-base font-semibold text-slate-900">
            {summary}
          </h2>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            className="inline-flex h-8 items-center gap-1 rounded-full border border-slate-200 bg-white px-2.5 text-[11px] font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-900"
            onClick={() => {
              void handleCopyJson();
            }}
            title="Copy JSON"
            aria-label="Copy JSON"
          >
            <span className="material-symbols-outlined text-[14px]">content_copy</span>
            <span>JSON</span>
          </button>
          <button
            type="button"
            className="inline-flex h-8 items-center gap-1 rounded-full border border-slate-200 bg-white px-2.5 text-[11px] font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-900"
            onClick={handleDownloadJson}
            title="Download JSON"
            aria-label="Download JSON"
          >
            <span className="material-symbols-outlined text-[14px]">download</span>
            <span>JSON</span>
          </button>
          <button
            type="button"
            className="inline-flex h-8 items-center gap-1 rounded-full border border-slate-200 bg-white px-2.5 text-[11px] font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-900"
            onClick={handleDownloadCsv}
            title="Download CSV for Excel"
            aria-label="Download CSV for Excel"
          >
            <span className="material-symbols-outlined text-[14px]">table_view</span>
            <span>CSV</span>
          </button>
        </div>
      </div>

      {premium ? (
        <p className="mt-3 break-words text-2xl font-semibold tracking-[-0.04em] text-emerald-700 sm:text-3xl">
          {premium}
        </p>
      ) : null}

      {exportStatus ? (
        <p className="mt-2 text-[11px] font-medium text-slate-500">{exportStatus}</p>
      ) : null}

      {entries.length ? (
        <dl className="mt-4 grid gap-2">
          {entries.map(([key, value]) => (
            <div
              key={key}
              className="ui-hover-lift rounded-xl border border-slate-200/80 bg-slate-50/80 px-3 py-2.5"
            >
              <dt className="text-[10px] uppercase tracking-[0.12em] text-slate-500">
                {key.replace(/_/g, " ")}
              </dt>
              <dd className="mt-1 break-words text-sm text-slate-900" style={{ overflowWrap: "anywhere" }}>
                {formatValue(value)}
              </dd>
            </div>
          ))}
        </dl>
      ) : null}

      {filteredEntries.length > entries.length ? (
        <p className="mt-4 text-xs text-slate-500">
          Showing the key quote details here to keep the chat focused.
        </p>
      ) : null}
    </section>
  );
}
