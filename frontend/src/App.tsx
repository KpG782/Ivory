"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ChatWindow } from "./components/ChatWindow";
import { IvoryLogo } from "./components/IvoryLogo";
import { Sidebar } from "./components/Sidebar";
import { useChat } from "./hooks/useChat";
import type { SessionSnapshot } from "./types";
import {
  checkAuthStatus,
  getDemoUsernameHint,
  isDemoLoginEnabled,
  serverDemoLogin,
  serverLogin,
  serverLogout,
} from "./lib/demoAuth";

const STEP_PROGRESS: Record<string, number> = {
  identify: 0.15,
  collect: 0.5,
  collect_details: 0.5,
  validate: 0.75,
  confirm: 1,
  quote: 1
};

function flowChipLabel(snapshot: SessionSnapshot | null): string | null {
  if (snapshot?.mode !== "transactional") {
    return null;
  }

  const product = snapshot.service_type
    ? `${snapshot.service_type} booking`
    : "Booking";
  const step = snapshot.intake_step
    ? snapshot.intake_step.replace(/_/g, " ")
    : "in progress";
  return `${product} · ${step}`;
}

function progressFraction(snapshot: SessionSnapshot | null): number | null {
  if (snapshot?.mode !== "transactional") {
    return null;
  }

  return STEP_PROGRESS[snapshot.intake_step ?? ""] ?? 0.3;
}

export default function App() {
  const chat = useChat();
  const [draft, setDraft] = useState("");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [desktopSidebarOpen, setDesktopSidebarOpen] = useState(true);
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
  const demoLoginEnabled = useMemo(() => isDemoLoginEnabled(), []);

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

  const handleDemoLogin = async () => {
    if (isAuthenticating) return;
    setIsAuthenticating(true);
    setAuthError(null);

    const { ok, error } = await serverDemoLogin();

    if (ok) {
      setIsAuthenticated(true);
      setPassword("");
    } else {
      setAuthError(error ?? "Demo login is not enabled.");
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
            {demoLoginEnabled ? (
              <>
                <button
                  type="button"
                  className="ui-hover-lift rounded-full bg-[#0F766E] px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#115E59] disabled:cursor-not-allowed disabled:bg-slate-300"
                  onClick={() => void handleDemoLogin()}
                  disabled={isAuthenticating}
                >
                  {isAuthenticating ? "Signing in..." : "Enter demo workspace"}
                </button>
                <div className="flex items-center gap-3 text-xs uppercase tracking-[0.18em] text-slate-400">
                  <span className="h-px flex-1 bg-slate-200" />
                  or sign in with credentials
                  <span className="h-px flex-1 bg-slate-200" />
                </div>
              </>
            ) : null}
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

  const conversationTitle = (() => {
    const firstUser = chat.messages.find(
      (message) => message.role === "user" && message.content.trim()
    );
    return firstUser ? firstUser.content.trim().slice(0, 60) : "Ivory";
  })();

  const flowChip = flowChipLabel(chat.sessionSnapshot);
  const progress = progressFraction(chat.sessionSnapshot);
  const statusChip = chat.isSending
    ? "Thinking…"
    : chat.sessionSnapshot?.has_booking_result
      ? "Booking ready"
      : chat.sessionSnapshot?.mode === "transactional"
        ? "Collecting details"
        : "Knowledge mode";

  return (
    <main className="ui-fade-in flex h-svh overflow-hidden bg-ivory text-ink">
      {mobileNavOpen ? (
        <button
          type="button"
          className="ui-fade-in fixed inset-0 z-30 bg-black/20 backdrop-blur-[1px] lg:hidden"
          onClick={() => setMobileNavOpen(false)}
          aria-label="Close sidebar overlay"
        />
      ) : null}

      <aside
        className={`hidden shrink-0 lg:block ${
          desktopSidebarOpen ? "w-[264px]" : "w-[64px]"
        }`}
      >
        <Sidebar
          sessions={chat.savedSessions}
          collapsed={!desktopSidebarOpen}
          userLabel={demoUsernameHint || "Workspace"}
          onNewConversation={chat.createNewSession}
          onRestoreSession={chat.restoreSession}
          onToggleCollapsed={() => setDesktopSidebarOpen((current) => !current)}
          onLogout={() => void handleLogout()}
        />
      </aside>

      {mobileNavOpen ? (
        <aside className="ui-slide-in-left fixed inset-y-0 left-0 z-40 w-[min(85vw,300px)] bg-ivory shadow-[0_20px_60px_rgba(28,25,23,0.18)] lg:hidden">
          <Sidebar
            sessions={chat.savedSessions}
            collapsed={false}
            userLabel={demoUsernameHint || "Workspace"}
            onNewConversation={() => {
              chat.createNewSession();
              setMobileNavOpen(false);
            }}
            onRestoreSession={(saved) => {
              chat.restoreSession(saved);
              setMobileNavOpen(false);
            }}
            onToggleCollapsed={() => setMobileNavOpen(false)}
            onLogout={() => void handleLogout()}
          />
        </aside>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-line/70 px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-2">
            <button
              type="button"
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-muted sm:h-9 sm:w-9 transition-colors hover:bg-soft hover:text-ink lg:hidden"
              onClick={() => setMobileNavOpen(true)}
              aria-label="Open sidebar"
            >
              <span className="material-symbols-outlined text-[20px]">menu</span>
            </button>
            <p className="truncate text-sm font-semibold text-ink">
              {conversationTitle}
            </p>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            {flowChip ? (
              <span className="inline-flex items-center rounded-full bg-teal-tint px-3 py-1 text-xs font-semibold capitalize text-teal">
                {flowChip}
              </span>
            ) : null}
            <span className="hidden items-center gap-1.5 rounded-full border border-line bg-white px-3 py-1 text-xs font-medium text-muted sm:inline-flex">
              <span
                className={`h-1.5 w-1.5 rounded-full bg-teal ${
                  chat.isSending ? "animate-pulse" : ""
                }`}
              />
              {statusChip}
            </span>
            <button
              type="button"
              className="flex h-11 w-11 items-center justify-center rounded-full text-muted sm:h-9 sm:w-9 transition-colors hover:bg-soft hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
              onClick={() => void chat.resetSession()}
              disabled={chat.isSending || chat.isResetting}
              aria-label="Reset session"
              title="Reset session"
            >
              <span className="material-symbols-outlined text-[20px]">
                refresh
              </span>
            </button>
          </div>
        </header>

        {progress !== null ? (
          <div
            className="h-[3px] w-full bg-soft"
            role="progressbar"
            aria-valuenow={Math.round(progress * 100)}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Quote progress"
          >
            <div
              className="h-full rounded-r-full bg-teal transition-all duration-300"
              style={{ width: `${progress * 100}%` }}
            />
          </div>
        ) : null}

        <ChatWindow
          messages={chat.messages}
          draft={draft}
          error={chat.error}
          isSending={chat.isSending}
          isResetting={chat.isResetting}
          hasQuoteResult={Boolean(chat.sessionSnapshot?.has_booking_result)}
          onDraftChange={setDraft}
          onSend={submitDraft}
          onStop={chat.stopGeneration}
          onQuickPrompt={(prompt) => void chat.sendMessage(prompt)}
        />
      </div>
    </main>
  );
}
