"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ChatWindow } from "./components/ChatWindow";
import { QuoteCard } from "./components/QuoteCard";
import { IvoryLogo } from "./components/IvoryLogo";
import { useChat } from "./hooks/useChat";
import {
  checkAuthStatus,
  getDemoUsernameHint,
  serverLogin,
  serverLogout,
} from "./lib/demoAuth";

function formatLabel(value: string | null | undefined, fallback: string) {
  if (!value) {
    return fallback;
  }

  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function StatePill({
  label,
  value
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="shrink-0 rounded-full border border-slate-200 bg-white px-3 py-1.5">
      <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">
        {label}
      </span>
      <span className="ml-2 text-xs font-semibold text-slate-700">{value}</span>
    </div>
  );
}

function NavItem({
  icon,
  label,
  collapsed,
  active = false,
  onClick
}: {
  icon: string;
  label: string;
  collapsed: boolean;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={collapsed ? label : undefined}
      aria-label={label}
      className={`ui-hover-lift flex w-full items-center rounded-xl text-left text-sm font-medium transition ${
        collapsed ? "justify-center px-0 py-3" : "gap-3 px-3 py-2.5"
      } ${
        active
          ? "bg-white text-slate-950 shadow-[0_8px_20px_rgba(15,23,42,0.06)]"
          : "text-slate-600 hover:bg-white hover:text-slate-950"
      }`}
    >
      <span className="material-symbols-outlined text-[18px] text-slate-500">
        {icon}
      </span>
      {!collapsed ? <span>{label}</span> : null}
    </button>
  );
}

export default function App() {
  const chat = useChat();
  const [draft, setDraft] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [authReady, setAuthReady] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const usernameInputRef = useRef<HTMLInputElement | null>(null);

  // Optional username hint from NEXT_PUBLIC_AUTH_DEMO_USER (safe to expose).
  // The password is never bundled into client code — it is validated server-side.
  const demoUsernameHint = useMemo(() => getDemoUsernameHint(), []);

  // Check auth status via the server-side /api/auth/check endpoint on mount.
  // This reads the httpOnly cookie; the client never sees the cookie value.
  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    checkAuthStatus()
      .then((authenticated) => {
        setIsAuthenticated(authenticated);
      })
      .catch(() => {
        setIsAuthenticated(false);
      })
      .finally(() => {
        setAuthReady(true);
      });
  }, []);

  // Move focus to the username field once the login screen is shown.
  useEffect(() => {
    if (authReady && !isAuthenticated) {
      usernameInputRef.current?.focus();
    }
  }, [authReady, isAuthenticated]);

  const submitDraft = async () => {
    const trimmed = draft.trim();
    if (!trimmed) {
      return;
    }

    setDraft("");
    await chat.sendMessage(trimmed);
  };

  const startNewQuote = () => {
    chat.createNewSession();
    setDraft("I need a quote for auto insurance.");
  };

  const handleAutofillUsername = () => {
    if (demoUsernameHint) {
      setUsername(demoUsernameHint);
      setAuthError(null);
    }
  };

  const handleLogin = async () => {
    if (isAuthenticating) return;
    setIsAuthenticating(true);
    setAuthError(null);

    const { ok, error } = await serverLogin(username.trim(), password);

    if (ok) {
      setIsAuthenticated(true);
      setPassword("");
    } else {
      setAuthError(error ?? "Invalid username or password.");
    }

    setIsAuthenticating(false);
  };

  const handleLogout = async () => {
    await serverLogout();
    setIsAuthenticated(false);
    setIsAuthenticating(false);
    setUsername("");
    setPassword("");
    setAuthError(null);
  };

  if (!authReady) {
    return <main className="min-h-screen" />;
  }

  if (!isAuthenticated) {
    return (
      <main className="ui-fade-in flex min-h-screen overflow-x-clip items-center justify-center px-4 py-8 text-[#191c1e]">
        <section className="ui-rise-in relative w-full max-w-md overflow-hidden rounded-[2rem] border border-black/8 bg-white/85 p-5 shadow-[0_20px_60px_rgba(15,23,42,0.08)] backdrop-blur sm:p-8">
          <div className="flex items-center gap-3">
            <IvoryLogo className="h-10 w-10 shrink-0" />
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">
                Ivory Access
              </p>
              <p className="mt-1 text-sm text-slate-500">Secure workspace entry</p>
            </div>
          </div>
          <h1 className="mt-3 font-[family-name:var(--font-display)] text-3xl font-bold tracking-[-0.04em] text-slate-950">
            Sign in to open the assistant
          </h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Enter your workspace credentials to continue.
          </p>
          <div className="mt-6 grid gap-4">
            <label className="grid gap-2">
              <span className="text-sm font-medium text-slate-700">Username</span>
              <input
                ref={usernameInputRef}
                className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-900 outline-none transition focus:border-[#bca46b] focus:ring-4 focus:ring-[#efe4c8]"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") void handleLogin(); }}
                placeholder="Enter username"
                autoComplete="username"
              />
            </label>
            <label className="grid gap-2">
              <span className="text-sm font-medium text-slate-700">Password</span>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 pr-12 text-slate-900 outline-none transition focus:border-[#bca46b] focus:ring-4 focus:ring-[#efe4c8]"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") void handleLogin(); }}
                  placeholder="Enter password"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute inset-y-0 right-0 flex items-center px-4 text-slate-400 transition hover:text-slate-700"
                >
                  <span className="material-symbols-outlined text-[20px]">
                    {showPassword ? "visibility_off" : "visibility"}
                  </span>
                </button>
              </div>
            </label>
            {demoUsernameHint ? (
              <button
                type="button"
                className="w-fit text-sm font-medium text-blue-600 transition hover:text-blue-700 hover:underline"
                onClick={handleAutofillUsername}
              >
                Autofill demo username
              </button>
            ) : null}
            {authError ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900">
                {authError}
              </div>
            ) : null}
            <button
              type="button"
              className="ui-hover-lift rounded-full bg-[#1f1f1f] px-4 py-3 text-sm font-semibold text-white transition hover:bg-black disabled:cursor-not-allowed disabled:bg-slate-300"
              onClick={() => void handleLogin()}
              disabled={isAuthenticating}
            >
              {isAuthenticating ? "Signing in..." : "Login"}
            </button>
          </div>
          {isAuthenticating ? (
            <div className="ui-fade-in absolute inset-0 flex items-center justify-center bg-[rgba(252,252,250,0.84)] backdrop-blur-sm">
              <div className="ui-rise-in flex flex-col items-center gap-4 rounded-[1.5rem] border border-black/8 bg-white/90 px-6 py-6 shadow-[0_18px_46px_rgba(15,23,42,0.08)]">
                <div className="ui-spin-slow flex h-14 w-14 items-center justify-center rounded-full border border-[#d9c69b] bg-[#f8f3e6] p-2.5 shadow-[0_10px_24px_rgba(0,81,213,0.12)]">
                  <IvoryLogo className="h-full w-full" />
                </div>
                <div className="text-center">
                  <p className="font-[family-name:var(--font-display)] text-lg font-bold text-slate-950">
                    Opening your workspace
                  </p>
                  <p className="mt-1 text-sm text-slate-500">
                    Restoring the latest assistant session.
                  </p>
                </div>
              </div>
            </div>
          ) : null}
        </section>
      </main>
    );
  }

  return (
    <main className="ui-fade-in min-h-screen overflow-x-clip text-[#191c1e]">
      {sidebarOpen ? (
        <button
          type="button"
          className="ui-fade-in fixed inset-0 z-30 bg-black/20 backdrop-blur-[1px] lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close sidebar overlay"
        />
      ) : null}

      <div className="mx-auto flex min-h-screen max-w-[1600px]">
        <aside
          className={`${
            sidebarOpen ? "w-[288px]" : "w-[88px]"
          } ui-slide-in-left fixed inset-y-0 left-0 z-40 hidden border-r border-black/8 bg-[rgba(250,250,247,0.88)] p-3 backdrop-blur lg:block`}
        >
          <div className="flex h-full min-h-0 flex-col gap-3">
            <div
              className={`ui-scale-in sticky top-0 z-10 rounded-[1.75rem] border border-black/8 bg-white/70 p-3 shadow-[0_12px_32px_rgba(15,23,42,0.05)] ${
                sidebarOpen ? "" : "items-center"
              }`}
            >
              <div className={`flex items-center ${sidebarOpen ? "justify-between" : "justify-center"}`}>
                {sidebarOpen ? (
                  <div className="flex items-center gap-3">
                    <IvoryLogo className="h-10 w-10 shrink-0" />
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">
                        Ivory
                      </p>
                      <p className="mt-1 text-sm text-slate-600">Workspace</p>
                    </div>
                  </div>
                ) : null}
                <button
                  type="button"
                  className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-700 transition hover:border-slate-300 hover:text-slate-950"
                  onClick={() => setSidebarOpen((current) => !current)}
                  aria-label={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
                >
                  <span className="material-symbols-outlined text-[20px]">
                    {sidebarOpen ? "left_panel_close" : "left_panel_open"}
                  </span>
                </button>
              </div>

              <div className={`mt-3 space-y-1 ${sidebarOpen ? "" : "mt-0"}`}>
                <NavItem
                  icon="chat_bubble"
                  label="Conversation"
                  collapsed={!sidebarOpen}
                  active
                />
              </div>

              {sidebarOpen ? (
                <div className="mt-4 flex flex-col gap-2">
                  <button
                    type="button"
                    className="ui-hover-lift rounded-full bg-[#1f1f1f] px-3.5 py-2 text-sm font-semibold text-white transition hover:bg-black"
                    onClick={startNewQuote}
                  >
                    New quote
                  </button>
                  <button
                    type="button"
                    className="ui-hover-lift rounded-full border border-slate-200 bg-white px-3.5 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-300 hover:text-slate-950"
                    onClick={() => void handleLogout()}
                  >
                    Logout
                  </button>
                </div>
              ) : null}
            </div>

            {sidebarOpen ? (
              <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pr-1">
                <section className="rounded-[1.75rem] border border-black/8 bg-white/70 p-5 shadow-[0_12px_32px_rgba(15,23,42,0.05)]">
                  <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">
                    Current state
                  </p>
                  <div className="mt-4 space-y-3">
                    <div className="rounded-xl bg-[#fafaf7] px-4 py-3">
                      <p className="text-[10px] uppercase tracking-[0.12em] text-slate-500">
                        Mode
                      </p>
                      <p className="mt-1 text-sm font-semibold text-slate-900">
                        {chat.sessionSnapshot?.mode === "transactional"
                          ? "Quote Flow"
                          : "Knowledge Mode"}
                      </p>
                    </div>
                    <div className="rounded-xl bg-[#fafaf7] px-4 py-3">
                      <p className="text-[10px] uppercase tracking-[0.12em] text-slate-500">
                        Step
                      </p>
                      <p className="mt-1 text-sm font-semibold text-slate-900">
                        {formatLabel(chat.sessionSnapshot?.quote_step, "General questions")}
                      </p>
                    </div>
                    {chat.sessionSnapshot?.insurance_type ? (
                      <div className="rounded-xl bg-[#fafaf7] px-4 py-3">
                        <p className="text-[10px] uppercase tracking-[0.12em] text-slate-500">
                          Product
                        </p>
                        <p className="mt-1 text-sm font-semibold text-slate-900">
                          {formatLabel(chat.sessionSnapshot.insurance_type, "Not selected")}
                        </p>
                      </div>
                    ) : null}
                    <div className="rounded-xl bg-[#fafaf7] px-4 py-3">
                      <p className="text-[10px] uppercase tracking-[0.12em] text-slate-500">
                        Status
                      </p>
                      <p className="mt-1 text-sm font-semibold text-slate-900">
                        {chat.statusText}
                      </p>
                    </div>
                  </div>
                </section>

                <section className="rounded-[1.75rem] border border-black/8 bg-white/70 p-5 shadow-[0_12px_32px_rgba(15,23,42,0.05)]">
                  <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">
                    Local history
                  </p>
                  <div className="mt-4 space-y-2">
                    {chat.savedSessions.slice(0, 6).map((saved) => (
                      <button
                        key={saved.sessionId}
                        type="button"
                        className="ui-hover-lift flex w-full min-w-0 flex-col items-start rounded-xl bg-[#fafaf7] px-4 py-3 text-left transition hover:bg-white"
                        onClick={() => chat.restoreSession(saved)}
                      >
                        <span className="w-full truncate text-sm font-semibold text-slate-900">
                          {saved.preview || "Conversation"}
                        </span>
                        <span className="mt-1 w-full break-words text-xs text-slate-500">
                          {saved.label} • {new Date(saved.updatedAt).toLocaleString()}
                        </span>
                      </button>
                    ))}
                    {!chat.savedSessions.length ? (
                      <p className="text-sm text-slate-500">
                        Local conversation history will appear here.
                      </p>
                    ) : null}
                  </div>
                </section>

                <QuoteCard quote={chat.quoteResult} variant="spotlight" />
              </div>
            ) : (
              <div className="ui-scale-in rounded-[1.75rem] border border-black/8 bg-white/70 p-2 shadow-[0_12px_32px_rgba(15,23,42,0.05)]">
                <div className="space-y-1">
                  <NavItem
                    icon="bolt"
                    label="New quote"
                    collapsed
                    onClick={startNewQuote}
                  />
                  <NavItem
                    icon="logout"
                    label="Logout"
                    collapsed
                    onClick={() => void handleLogout()}
                  />
                </div>
              </div>
            )}
          </div>
        </aside>

        {sidebarOpen ? (
          <aside className="ui-slide-in-left fixed inset-y-0 left-0 z-40 w-[min(88vw,320px)] max-w-full border-r border-black/8 bg-[rgba(250,250,247,0.96)] p-3 shadow-[0_20px_60px_rgba(15,23,42,0.18)] backdrop-blur sm:p-4 lg:hidden">
            <div className="flex h-full flex-col gap-4 overflow-auto">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <IvoryLogo className="h-10 w-10 shrink-0" />
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">
                      Ivory
                    </p>
                    <p className="mt-1 text-sm text-slate-600">Workspace</p>
                  </div>
                </div>
                <button
                  type="button"
                  className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-700"
                  onClick={() => setSidebarOpen(false)}
                  aria-label="Close sidebar"
                >
                  <span className="material-symbols-outlined text-[20px]">close</span>
                </button>
              </div>

              <div className="sticky top-0 z-10 rounded-[1.75rem] border border-black/8 bg-white/80 p-3">
                <div className="space-y-1">
                  <NavItem icon="chat_bubble" label="Conversation" collapsed={false} active />
                </div>
                <div className="mt-4 flex flex-col gap-2">
                  <button
                    type="button"
                    className="ui-hover-lift rounded-full bg-[#1f1f1f] px-3.5 py-2 text-sm font-semibold text-white"
                    onClick={() => {
                      startNewQuote();
                      setSidebarOpen(false);
                    }}
                  >
                    New quote
                  </button>
                  <button
                    type="button"
                    className="ui-hover-lift rounded-full border border-slate-200 bg-white px-3.5 py-2 text-sm font-semibold text-slate-700"
                    onClick={() => void handleLogout()}
                  >
                    Logout
                  </button>
                </div>
              </div>

              <section className="rounded-[1.75rem] border border-black/8 bg-white/80 p-5">
                <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">
                  Local history
                </p>
                <div className="mt-4 space-y-2">
                  {chat.savedSessions.slice(0, 5).map((saved) => (
                    <button
                      key={saved.sessionId}
                      type="button"
                      className="ui-hover-lift flex w-full min-w-0 flex-col items-start rounded-xl bg-[#fafaf7] px-4 py-3 text-left"
                      onClick={() => {
                        chat.restoreSession(saved);
                        setSidebarOpen(false);
                      }}
                    >
                      <span className="w-full truncate text-sm font-semibold text-slate-900">
                        {saved.preview || "Conversation"}
                      </span>
                      <span className="mt-1 w-full break-words text-xs text-slate-500">
                        {saved.label} • {new Date(saved.updatedAt).toLocaleString()}
                      </span>
                    </button>
                  ))}
                  {!chat.savedSessions.length ? (
                    <p className="text-sm text-slate-500">
                      Local conversation history will appear here.
                    </p>
                  ) : null}
                </div>
              </section>

              <QuoteCard quote={chat.quoteResult} variant="spotlight" />
            </div>
          </aside>
        ) : null}

        <section
          className={`min-w-0 flex-1 ${sidebarOpen ? "lg:pl-[288px]" : "lg:pl-[88px]"}`}
        >
          <div className="min-w-0 px-3 py-3 sm:px-4 sm:py-4 md:px-6 md:py-6">
            <header className="ui-rise-in sticky top-3 z-10 mb-4 flex flex-wrap items-center justify-between gap-3 rounded-[1.5rem] border border-black/8 bg-[rgba(252,252,250,0.92)] px-3 py-3 shadow-[0_10px_24px_rgba(15,23,42,0.06)] backdrop-blur sm:top-4 sm:px-4">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-700 transition hover:border-slate-300 hover:text-slate-950 lg:hidden"
                  onClick={() => setSidebarOpen(true)}
                  aria-label="Open sidebar"
                >
                  <span className="material-symbols-outlined text-[20px]">menu</span>
                </button>
                <div className="flex items-center gap-3">
                  <IvoryLogo className="h-10 w-10 shrink-0" />
                  <div>
                  <p className="font-[family-name:var(--font-display)] text-lg font-bold text-slate-950">
                    Ivory
                  </p>
                  <p className="text-sm text-slate-500">
                    Chat-first quote workspace
                  </p>
                  </div>
                </div>
              </div>

              <div className="-mx-1 flex w-[calc(100%+0.5rem)] gap-2 overflow-x-auto px-1 pb-1 text-xs text-slate-500 sm:mx-0 sm:w-auto sm:flex-wrap sm:justify-end sm:overflow-visible sm:px-0 sm:pb-0">
                <button
                  type="button"
                  className="ui-hover-lift hidden rounded-full border border-slate-200 bg-white px-3 py-1.5 transition hover:border-slate-300 hover:text-slate-900 lg:inline-flex"
                  onClick={() => setSidebarOpen((current) => !current)}
                >
                  {sidebarOpen ? "Collapse panel" : "Expand panel"}
                </button>
                <StatePill
                  label="Mode"
                  value={
                    chat.sessionSnapshot?.mode === "transactional"
                      ? "Quote Flow"
                      : "Knowledge Mode"
                  }
                />
                <StatePill
                  label="Step"
                  value={formatLabel(chat.sessionSnapshot?.quote_step, "General questions")}
                />
              </div>
            </header>

            <ChatWindow
              messages={chat.messages}
              draft={draft}
              error={chat.error}
              isSending={chat.isSending}
              isResetting={chat.isResetting}
              sessionLabel={chat.sessionLabel}
              quoteResult={chat.quoteResult}
              statusText={chat.statusText}
              onDraftChange={setDraft}
              onSend={submitDraft}
              onReset={chat.resetSession}
              onNewSession={chat.createNewSession}
              onStop={chat.stopGeneration}
              onQuickPrompt={(prompt) => {
                setDraft(prompt);
              }}
            />
          </div>
        </section>
      </div>
    </main>
  );
}
