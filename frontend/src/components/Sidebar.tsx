"use client";

import { IvoryLogo } from "./IvoryLogo";
import type { SavedChatSession } from "../types";

function groupLabel(updatedAt: string): "Today" | "Yesterday" | "Older" {
  const date = new Date(updatedAt);
  const now = new Date();
  const startOfDay = (d: Date) =>
    new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const diffDays = Math.round((startOfDay(now) - startOfDay(date)) / 86_400_000);
  if (diffDays <= 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  return "Older";
}

function groupSessions(sessions: SavedChatSession[]) {
  const groups: { label: string; items: SavedChatSession[] }[] = [];
  for (const session of sessions) {
    const label = groupLabel(session.updatedAt);
    const existing = groups.find((group) => group.label === label);
    if (existing) {
      existing.items.push(session);
    } else {
      groups.push({ label, items: [session] });
    }
  }
  return groups;
}

interface SidebarProps {
  sessions: SavedChatSession[];
  collapsed: boolean;
  userLabel: string;
  onNewConversation: () => void;
  onRestoreSession: (saved: SavedChatSession) => void;
  onToggleCollapsed: () => void;
  onLogout: () => void;
}

export function Sidebar({
  sessions,
  collapsed,
  userLabel,
  onNewConversation,
  onRestoreSession,
  onToggleCollapsed,
  onLogout
}: SidebarProps) {
  const userInitial = (userLabel.trim()[0] || "W").toUpperCase();

  if (collapsed) {
    return (
      <div className="flex h-full flex-col items-center border-r border-line bg-soft/60 py-5">
        <button
          type="button"
          onClick={onToggleCollapsed}
          aria-label="Expand sidebar"
          className="rounded-xl transition-opacity hover:opacity-80"
        >
          <IvoryLogo className="h-8 w-8" />
        </button>
        <button
          type="button"
          onClick={onNewConversation}
          aria-label="New conversation"
          className="mt-5 flex h-10 w-10 items-center justify-center rounded-full bg-teal text-white transition-colors hover:bg-teal-hover"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" d="M12 5v14M5 12h14" />
          </svg>
        </button>
        <div className="mt-auto">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-teal-tint text-xs font-bold text-teal">
            {userInitial}
          </span>
        </div>
      </div>
    );
  }

  const groups = groupSessions(sessions);

  return (
    <div className="flex h-full flex-col border-r border-line bg-soft/60">
      <div className="flex items-center justify-between px-4 pt-5">
        <div className="flex items-center gap-2.5">
          <IvoryLogo className="h-8 w-8" />
          <span className="font-[family-name:var(--font-display)] text-xl text-ink">
            Ivory
          </span>
        </div>
        <button
          type="button"
          onClick={onToggleCollapsed}
          aria-label="Collapse sidebar"
          className="hidden h-8 w-8 items-center justify-center rounded-full text-muted transition-colors hover:bg-white hover:text-ink lg:flex"
        >
          <span className="material-symbols-outlined text-[18px]">left_panel_close</span>
        </button>
      </div>

      <div className="px-3 pt-5">
        <button
          type="button"
          onClick={onNewConversation}
          className="flex w-full items-center gap-2 rounded-full bg-teal px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-teal-hover"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" d="M12 5v14M5 12h14" />
          </svg>
          New conversation
        </button>
      </div>

      <nav className="mt-5 flex-1 space-y-4 overflow-y-auto px-3 pb-3" aria-label="Conversation history">
        {groups.map((group) => (
          <div key={group.label}>
            <p className="px-2 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted/70">
              {group.label}
            </p>
            {group.items.map((saved) => (
              <button
                key={saved.sessionId}
                type="button"
                onClick={() => onRestoreSession(saved)}
                className="block w-full truncate rounded-lg px-3 py-2 text-left text-sm text-ink/90 transition-colors hover:bg-white"
                title={saved.preview || "Conversation"}
              >
                {saved.preview || "Conversation"}
              </button>
            ))}
          </div>
        ))}
        {!groups.length ? (
          <p className="px-3 text-sm leading-6 text-muted">
            Completed conversations will appear here.
          </p>
        ) : null}
      </nav>

      <div className="border-t border-line p-3">
        <div className="flex items-center gap-2.5 rounded-lg px-2 py-1.5">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-teal-tint text-xs font-bold text-teal">
            {userInitial}
          </span>
          <span className="min-w-0 flex-1 truncate text-sm font-medium text-ink">
            {userLabel}
          </span>
          <button
            type="button"
            onClick={onLogout}
            aria-label="Log out"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-muted transition-colors hover:bg-white hover:text-ink"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
