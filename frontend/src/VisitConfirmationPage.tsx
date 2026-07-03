"use client";

import Link from "next/link";
import { useMemo } from "react";
import { QuoteCard } from "./components/QuoteCard";
import { IvoryLogo } from "./components/IvoryLogo";
import { useChat } from "./hooks/useChat";

function formatInsuranceLabel(value: string | null | undefined): string {
  if (!value) {
    return "Insurance";
  }
  return `${value.charAt(0).toUpperCase()}${value.slice(1)} Quote`;
}

export default function QuoteConfirmationPage() {
  const chat = useChat();

  const isConfirmationReady = useMemo(() => {
    return (
      chat.sessionSnapshot?.quote_step === "confirm" &&
      chat.sessionSnapshot?.mode === "transactional" &&
      !!chat.quoteResult
    );
  }, [chat.quoteResult, chat.sessionSnapshot]);

  const pageTitle = formatInsuranceLabel(chat.sessionSnapshot?.insurance_type);

  return (
    <main className="min-h-screen px-3 py-4 text-[#191c1e] sm:px-4 sm:py-6 md:px-8">
      <div className="mx-auto flex max-w-5xl flex-col gap-6 md:gap-8">
        <header className="flex flex-col gap-4 rounded-[1.75rem] border border-black/8 bg-white/75 px-4 py-4 shadow-[0_12px_32px_rgba(15,23,42,0.05)] backdrop-blur sm:px-6 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-4">
            <IvoryLogo className="h-10 w-10 shrink-0" />
            <span className="font-[family-name:var(--font-display)] text-xl font-bold tracking-tight text-slate-900">
              Ivory
            </span>
            <nav className="hidden items-center space-x-3 text-sm text-slate-500 md:flex">
              <span>Home</span>
              <span>/</span>
              <span>Chat</span>
              <span>/</span>
              <span className="font-semibold text-slate-900">Confirmation</span>
            </nav>
          </div>
          <Link
            href="/"
            className="inline-flex rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:text-slate-950"
          >
            Back to chat
          </Link>
        </header>

        <section className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center space-x-2 text-slate-500">
            <span className="text-xs font-medium uppercase tracking-[0.18em]">
              {pageTitle}
            </span>
            <span className="material-symbols-outlined text-sm">chevron_right</span>
            <span className="text-xs font-bold uppercase tracking-[0.18em] text-slate-900">
              Final Confirmation
            </span>
          </div>
          <div className="inline-flex items-center gap-2 rounded-full bg-emerald-100 px-3 py-1.5">
            <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-600" />
            <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-emerald-900">
              AI Transactional Mode
            </span>
          </div>
        </section>

        {isConfirmationReady ? (
          <section className="space-y-8">
            <div className="flex justify-end">
              <div className="max-w-[80%] rounded-[1.35rem] bg-[#1f1f1f] px-5 py-3 text-white shadow-[0_10px_30px_rgba(15,23,42,0.14)]">
                <p className="font-medium">
                  Confirm my quote for the current policy and coverage options.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 md:gap-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-slate-900 text-white">
                <IvoryLogo className="h-6 w-6" />
              </div>

              <div className="flex-1 space-y-6">
                <div className="max-w-2xl rounded-[1.5rem] rounded-bl-sm border border-black/8 bg-white/90 p-6 shadow-[0_10px_24px_rgba(15,23,42,0.06)]">
                  <p className="text-lg leading-relaxed text-slate-900">
                    Great news. Your personalized quote is ready for final review.
                  </p>
                </div>

                <div className="overflow-hidden rounded-[1.6rem] border border-black/8 bg-white/95 shadow-[0_16px_40px_rgba(15,23,42,0.08)] backdrop-blur">
                  <div className="flex flex-col gap-3 bg-[#f6f4ee] px-5 py-5 sm:px-6 md:flex-row md:items-center md:justify-between md:px-8">
                    <div>
                      <h3 className="font-[family-name:var(--font-display)] text-xl font-extrabold text-slate-900">
                        Insurance Quote Summary
                      </h3>
                      <p className="text-sm text-slate-500">
                        Quote ID: {chat.sessionSnapshot?.session_id ?? "pending"}
                      </p>
                    </div>
                    <div className="inline-flex items-center gap-2 rounded-full bg-emerald-100 px-4 py-2 font-bold text-emerald-950">
                      <span className="material-symbols-outlined text-sm">verified</span>
                      Best Value
                    </div>
                  </div>

                  <div className="p-5 sm:p-6 md:p-8">
                    {chat.quoteResult ? <QuoteCard quote={chat.quoteResult} /> : null}
                  </div>

                  <div className="flex flex-col gap-3 px-5 pb-6 pt-2 sm:px-6 md:flex-row md:gap-4 md:px-8 md:pb-8">
                    <button
                      type="button"
                      className="flex-1 rounded-full bg-[#1f1f1f] px-6 py-4 font-[family-name:var(--font-display)] font-bold text-white transition hover:bg-black"
                      onClick={() => {
                        void chat.sendMessage("accept");
                      }}
                    >
                      Accept &amp; Buy Now
                    </button>
                    <button
                      type="button"
                      className="flex-1 rounded-full border border-slate-300 px-6 py-4 font-[family-name:var(--font-display)] font-bold text-slate-900 transition hover:bg-slate-50"
                      onClick={() => {
                        void chat.sendMessage("adjust");
                      }}
                    >
                      Adjust Coverage
                    </button>
                    <button
                      type="button"
                      className="px-4 py-3 text-left font-[family-name:var(--font-display)] font-bold text-slate-500 transition hover:text-slate-900 md:px-6 md:py-4 md:text-center"
                    >
                      Talk to an Agent
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </section>
        ) : (
          <section className="rounded-[1.6rem] border border-black/8 bg-white/90 p-8 shadow-[0_12px_32px_rgba(15,23,42,0.05)] backdrop-blur">
            <h1 className="font-[family-name:var(--font-display)] text-2xl font-bold text-slate-900">
              Confirmation isn&apos;t ready yet
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
              This page is only meant for the backend&apos;s quote confirmation state.
              Start or continue a quote in chat until the backend returns a session
              snapshot with <code>quote_step = confirm</code>.
            </p>
            <div className="mt-6">
              <Link
                href="/"
                className="inline-flex rounded-full bg-[#1f1f1f] px-4 py-2 text-sm font-semibold text-white transition hover:bg-black"
              >
                Return to chat
              </Link>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
