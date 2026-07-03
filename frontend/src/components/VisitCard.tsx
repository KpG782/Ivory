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
  quote: QuoteResult;
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

export function QuoteCard({ quote }: QuoteCardProps) {
  const [exportStatus, setExportStatus] = useState<string | null>(null);

  const premium = formatCurrency(quote);
  const product = quote.product_type
    ? `${String(quote.product_type)} insurance quote`
    : "Insurance quote";
  const coverage = quote.coverage_level ? String(quote.coverage_level) : null;

  const filteredEntries = useMemo(() => {
    return Object.entries(quote).filter(
      ([key, value]) =>
        ![
          "summary",
          "product_type",
          "premium",
          "annual_premium",
          "currency",
          "coverage_level"
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
      .slice(0, 4);
  }, [filteredEntries]);

  async function handleCopyJson(): Promise<void> {
    const json = toPrettyJson(quote);
    try {
      await navigator.clipboard.writeText(json);
      setExportStatus("JSON copied");
    } catch {
      setExportStatus("Copy failed");
    }
  }

  function handleDownloadJson(): void {
    downloadTextFile(
      buildExportFileName(quote, "json"),
      toPrettyJson(quote),
      "application/json;charset=utf-8"
    );
    setExportStatus("JSON downloaded");
  }

  function handleDownloadCsv(): void {
    downloadTextFile(
      buildExportFileName(quote, "csv"),
      toCsv(quote),
      "text/csv;charset=utf-8"
    );
    setExportStatus("CSV downloaded");
  }

  return (
    <section className="ui-scale-in min-w-0 overflow-hidden rounded-xl border border-line bg-white shadow-sm">
      <div className="flex items-center justify-between gap-3 border-b border-line bg-soft/50 px-4 py-3">
        <p className="min-w-0 truncate text-sm font-semibold capitalize text-ink">
          {product}
        </p>
        {coverage ? (
          <span className="shrink-0 rounded-full bg-teal-tint px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide text-teal">
            {coverage}
          </span>
        ) : null}
      </div>

      {entries.length ? (
        <dl className="space-y-2 px-4 py-3 text-sm">
          {entries.map(([key, value]) => (
            <div key={key} className="flex justify-between gap-3">
              <dt className="capitalize text-muted">{key.replace(/_/g, " ")}</dt>
              <dd
                className="break-words text-right font-medium text-ink"
                style={{ overflowWrap: "anywhere" }}
              >
                {formatValue(value)}
              </dd>
            </div>
          ))}
        </dl>
      ) : null}

      {premium ? (
        <div className="flex items-baseline justify-between border-t border-line px-4 py-3">
          <span className="text-sm font-semibold text-ink">Premium</span>
          <span className="font-[family-name:var(--font-display)] text-xl text-teal">
            {premium}
            <span className="ml-1 font-sans text-xs text-muted">/yr</span>
          </span>
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-1.5 px-4 pb-4">
        <button
          type="button"
          className="inline-flex h-8 items-center gap-1 rounded-full border border-line bg-white px-2.5 text-[11px] font-medium text-muted transition-colors hover:border-teal hover:text-teal"
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
          className="inline-flex h-8 items-center gap-1 rounded-full border border-line bg-white px-2.5 text-[11px] font-medium text-muted transition-colors hover:border-teal hover:text-teal"
          onClick={handleDownloadJson}
          title="Download JSON"
          aria-label="Download JSON"
        >
          <span className="material-symbols-outlined text-[14px]">download</span>
          <span>JSON</span>
        </button>
        <button
          type="button"
          className="inline-flex h-8 items-center gap-1 rounded-full border border-line bg-white px-2.5 text-[11px] font-medium text-muted transition-colors hover:border-teal hover:text-teal"
          onClick={handleDownloadCsv}
          title="Download CSV for Excel"
          aria-label="Download CSV for Excel"
        >
          <span className="material-symbols-outlined text-[14px]">table_view</span>
          <span>CSV</span>
        </button>
        {exportStatus ? (
          <span className="text-[11px] font-medium text-muted" role="status">
            {exportStatus}
          </span>
        ) : null}
      </div>
    </section>
  );
}
