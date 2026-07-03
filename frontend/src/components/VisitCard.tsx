"use client";

import { useMemo, useState } from "react";
import type { VisitEstimate } from "../types";

/** Canonical dental-first ordering for detail rows and exports. */
const DENTAL_FIELD_ORDER = [
  "service_type",
  "summary",
  "estimate_low",
  "estimate_high",
  "currency",
  "patient_name",
  "contact_email",
  "contact_phone",
  "last_visit_year",
  "insurance_status",
  "preferred_time",
  "issue_type",
  "pain_level",
  "treatment",
  "budget_band",
  "timeline",
  "disclaimer"
];

/** Fields rendered elsewhere on the card (header, range figure, footnote). */
const DETAIL_HIDDEN_FIELDS = [
  "summary",
  "service_type",
  "estimate_low",
  "estimate_high",
  "currency",
  "disclaimer"
];

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

function formatEstimateRange(estimate: VisitEstimate): string | null {
  const low =
    typeof estimate.estimate_low === "number" ? estimate.estimate_low : null;
  const high =
    typeof estimate.estimate_high === "number" ? estimate.estimate_high : null;

  if (low === null && high === null) {
    return null;
  }

  const formatter = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: estimate.currency || "USD"
  });

  if (low !== null && high !== null) {
    return `${formatter.format(low)}–${formatter.format(high)}`;
  }

  return formatter.format((low ?? high) as number);
}

function sanitizeFilePart(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "estimate";
}

function buildExportFileName(estimate: VisitEstimate, extension: string): string {
  const service = sanitizeFilePart(String(estimate.service_type || "visit"));
  return `ivory-${service}-estimate.${extension}`;
}

function dentalFieldRank(key: string): number {
  const index = DENTAL_FIELD_ORDER.indexOf(key);
  return index === -1 ? DENTAL_FIELD_ORDER.length : index;
}

function orderedEntries(estimate: VisitEstimate): [string, unknown][] {
  return Object.entries(estimate).sort(
    ([left], [right]) => dentalFieldRank(left) - dentalFieldRank(right)
  );
}

function toPrettyJson(estimate: VisitEstimate): string {
  return JSON.stringify(Object.fromEntries(orderedEntries(estimate)), null, 2);
}

function toCsv(estimate: VisitEstimate): string {
  const rows = orderedEntries(estimate).map(([key, value]) => [
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

interface VisitCardProps {
  estimate: VisitEstimate;
}

export function VisitCard({ estimate }: VisitCardProps) {
  const [exportStatus, setExportStatus] = useState<string | null>(null);

  const range = formatEstimateRange(estimate);
  const heading = estimate.summary
    ? String(estimate.summary)
    : estimate.service_type
      ? `${String(estimate.service_type)} visit estimate`
      : "Visit estimate";
  const service = estimate.service_type ? String(estimate.service_type) : null;
  const disclaimer =
    typeof estimate.disclaimer === "string" && estimate.disclaimer.trim()
      ? estimate.disclaimer
      : null;

  const entries = useMemo(() => {
    return orderedEntries(estimate).filter(
      ([key, value]) =>
        !DETAIL_HIDDEN_FIELDS.includes(key) &&
        value !== undefined &&
        value !== null &&
        value !== ""
    );
  }, [estimate]);

  async function handleCopyJson(): Promise<void> {
    const json = toPrettyJson(estimate);
    try {
      await navigator.clipboard.writeText(json);
      setExportStatus("JSON copied");
    } catch {
      setExportStatus("Copy failed");
    }
  }

  function handleDownloadJson(): void {
    downloadTextFile(
      buildExportFileName(estimate, "json"),
      toPrettyJson(estimate),
      "application/json;charset=utf-8"
    );
    setExportStatus("JSON downloaded");
  }

  function handleDownloadCsv(): void {
    downloadTextFile(
      buildExportFileName(estimate, "csv"),
      toCsv(estimate),
      "text/csv;charset=utf-8"
    );
    setExportStatus("CSV downloaded");
  }

  return (
    <section className="ui-scale-in min-w-0 overflow-hidden rounded-xl border border-line bg-white shadow-sm">
      <div className="flex items-center justify-between gap-3 border-b border-line bg-soft/50 px-4 py-3">
        <p className="min-w-0 truncate text-sm font-semibold text-ink">
          {heading}
        </p>
        {service ? (
          <span className="shrink-0 rounded-full bg-teal-tint px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide text-teal">
            {service}
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

      {range ? (
        <div className="flex items-baseline justify-between border-t border-line px-4 py-3">
          <span className="text-sm font-semibold text-ink">Estimated cost</span>
          <span className="font-[family-name:var(--font-display)] text-xl text-teal">
            {range}
            <span className="ml-1 font-sans text-xs text-muted">range</span>
          </span>
        </div>
      ) : null}

      {disclaimer ? (
        <p className="px-4 pb-3 text-[11px] leading-4 text-muted">{disclaimer}</p>
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
