# Modern Chat UI Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the Ivory workspace as a conversation-first layout (ChatGPT-pattern) per `docs/specs/MODERN_CHAT_UI_REDESIGN.md`, keeping `useChat`, backend contracts, and the login screen untouched.

**Architecture:** Pure frontend restyle/reorganization. New `Sidebar` component absorbs history/new-conversation/logout; `App.tsx` becomes a thin shell (sidebar + slim header + `ChatWindow`); `ChatWindow` becomes the centered conversation column with welcome state and pill composer; `MessageBubble` goes asymmetric (flat assistant / teal user bubble); `QuoteCard` keeps all export logic, loses the `spotlight` variant.

**Tech Stack:** Next.js App Router, Tailwind v4 (`@theme` tokens), `next/font` (Inter + Playfair Display), existing `useChat` hook (unchanged).

**Verification model:** The frontend has no unit-test runner (and adding one is out of scope for a visual restyle), so every task verifies with `npx tsc --noEmit` and the final task does a Playwright click-through + screenshots at 1280×800 and 375×812. Backend suite (41 tests) must stay green — it is untouched, run it once at the end to prove it. Visual source of truth: `docs/design/mockups/ivory-modern-chat.html`.

---

### Task 1: Design tokens + fonts

**Files:**
- Modify: `frontend/app/layout.tsx`
- Modify: `frontend/app/globals.css` (`@theme` block + `:root` + `body` background only; keep `ui-*` animation classes and their `prefers-reduced-motion` gates)

- [ ] **Step 1: Swap fonts in `layout.tsx`**

```tsx
import { Inter, Playfair_Display } from "next/font/google";

const bodyFont = Inter({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap"
});

const displayFont = Playfair_Display({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap"
});
```

Keep the Material Symbols `<link>` (icons still used), `metadata`, and body className as-is.

- [ ] **Step 2: Replace the Tailwind theme tokens in `globals.css`**

Replace the existing `@theme` block with:

```css
@theme {
  --color-ivory: #FAFAF9;
  --color-ink: #1C1917;
  --color-muted: #57534E;
  --color-teal: #0F766E;
  --color-teal-hover: #115E59;
  --color-teal-tint: #CCFBF1;
  --color-line: #E7E5E4;
  --color-soft: #F5F5F4;
  --font-sans: var(--font-body);
  --font-display: var(--font-display);
  --shadow-panel: 0 20px 60px rgba(28, 25, 23, 0.08);
}
```

- [ ] **Step 3: Flatten the page background in `:root` / `body`**

```css
:root {
  color-scheme: light;
  --page-background: #FAFAF9;
  --card-background: #FFFFFF;
  --card-strong: #FFFFFF;
  --line-soft: #E7E5E4;
  --line-strong: #D6D3D1;
}
```

Delete the `body::before` decorative overlay if it paints a gradient/noise. Keep
`overflow-x: hidden`, smooth scroll, and the `ui-*` keyframes.

- [ ] **Step 4: Typecheck + visual smoke**

Run: `cd frontend && npx tsc --noEmit` → expect clean.
Dev server still renders (background turns flat ivory, fonts swap).

- [ ] **Step 5: Commit**

```bash
git add frontend/app/layout.tsx frontend/app/globals.css
git commit -m "ui: Ivory tokens + Inter/Playfair fonts"
```

---

### Task 2: `Sidebar` component (new)

**Files:**
- Create: `frontend/src/components/Sidebar.tsx`

Props (all data in, callbacks out — no hook calls inside):

```tsx
import { IvoryLogo } from "./IvoryLogo";
import type { SavedChatSession } from "../types";

interface SidebarProps {
  sessions: SavedChatSession[];
  collapsed: boolean;
  userLabel: string;            // demo hint or "Workspace"
  onNewConversation: () => void;
  onRestoreSession: (saved: SavedChatSession) => void;
  onToggleCollapsed: () => void;
  onLogout: () => void;
}
```

- [ ] **Step 1: Implement history grouping (top of file, pure function)**

```tsx
function groupLabel(updatedAt: string): "Today" | "Yesterday" | "Older" {
  const date = new Date(updatedAt);
  const now = new Date();
  const startOfDay = (d: Date) =>
    new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const diffDays = Math.round(
    (startOfDay(now) - startOfDay(date)) / 86_400_000
  );
  if (diffDays <= 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  return "Older";
}

function groupSessions(sessions: SavedChatSession[]) {
  const groups: { label: string; items: SavedChatSession[] }[] = [];
  for (const session of sessions) {
    const label = groupLabel(session.updatedAt);
    const existing = groups.find((g) => g.label === label);
    if (existing) existing.items.push(session);
    else groups.push({ label, items: [session] });
  }
  return groups;
}
```

- [ ] **Step 2: Implement the two render modes**

Expanded (264px): logo + `font-[family-name:var(--font-display)]` wordmark,
teal "New conversation" pill button, grouped history list (truncated
`session.preview`, hover `bg-white`), footer user chip + logout icon button.
Collapsed (64px): logo, round teal "+" button, footer initial chip.
Use the mockup's exact classes (`docs/design/mockups/ivory-modern-chat.html`,
sidebar sections of Screen 1 and Screen 2) translated to the theme tokens:
`bg-soft/60`, `border-line`, `bg-teal hover:bg-teal-hover`, etc.
Every button: `cursor-pointer`, color-only hover transitions.

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npx tsc --noEmit` → clean (component not yet mounted).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Sidebar.tsx
git commit -m "ui: conversation-history sidebar component"
```

---

### Task 3: `MessageBubble` → asymmetric messages

**Files:**
- Modify: `frontend/src/components/MessageBubble.tsx`

- [ ] **Step 1: Restyle**

Keep: memoization, `MessageBody` (Markdown for assistant / verbatim for user),
TypingIndicator while streaming-empty, inline `QuoteCard` when
`message.quoteResult`. Replace the bubble layout:

```tsx
// assistant: flat row — avatar + body, no card
if (message.role === "assistant") {
  return (
    <article className="ui-rise-in flex gap-3">
      <IvoryLogo className="mt-0.5 h-7 w-7 shrink-0" />
      <div className="min-w-0 flex-1">
        <div
          className={`text-[15px] leading-7 text-ink ${
            message.kind === "error"
              ? "rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-rose-950"
              : ""
          }`}
          style={{ overflowWrap: "anywhere" }}
        >
          <MessageBody message={message} />
        </div>
        {message.quoteResult ? (
          <div className="mt-3 max-w-md">
            <QuoteCard quote={message.quoteResult} />
          </div>
        ) : null}
      </div>
    </article>
  );
}

// user: right-aligned teal bubble
return (
  <article className="ui-rise-in flex justify-end">
    <div
      className="max-w-[75%] rounded-2xl rounded-br-md bg-teal px-4 py-2.5 text-[15px] leading-6 text-white"
      style={{ overflowWrap: "anywhere" }}
    >
      <MessageBody message={message} />
    </div>
  </article>
);
```

Drop the "You / Ivory / Live" label row entirely (avatars + alignment carry the
roles; streaming is conveyed by the TypingIndicator and composer state). The
`kind === "info"` welcome message renders as a normal assistant message.

- [ ] **Step 2: Typecheck + commit**

```bash
cd frontend && npx tsc --noEmit
git add frontend/src/components/MessageBubble.tsx
git commit -m "ui: flat assistant messages, teal user bubbles"
```

---

### Task 4: `QuoteCard` → inline thread card only

**Files:**
- Modify: `frontend/src/components/QuoteCard.tsx`
- Modify: `frontend/src/App.tsx` (delete both `variant="spotlight"` usages — happens in Task 6's rewrite; the prop is removed here)

- [ ] **Step 1: Remove the `variant` prop and null-quote placeholder**

The card now renders only inside a message that has a quote, so `quote` becomes
required and the "Draft quote in progress" empty state is deleted. Keep ALL
export logic (copy/download JSON, CSV) and field prioritization untouched.

- [ ] **Step 2: Restyle to mockup Screen 2's quote card**

Structure: white `rounded-xl border border-line shadow-sm` card →
header row (`bg-soft/50` strip: "{product} quote" + teal-tint coverage badge) →
`dl` rows (muted label left, medium value right, plain — no per-row cards) →
premium row separated by `border-t`: label + `font-[family-name:var(--font-display)] text-xl text-teal`
figure → export buttons as small outline pills in the footer.

- [ ] **Step 3: Typecheck + commit**

`npx tsc --noEmit` will fail on App.tsx's `spotlight` usages until Task 6 — if
committing this task independently, leave the `variant` prop accepted-but-ignored
and delete it in Task 6 instead. (Executing inline in one session: remove it here
and fix App.tsx in the same working tree before the commit at the end of Task 6.)

```bash
git add frontend/src/components/QuoteCard.tsx
git commit -m "ui: inline quote card restyle"
```

---

### Task 5: `ChatWindow` → centered conversation column

**Files:**
- Modify: `frontend/src/components/ChatWindow.tsx`

- [ ] **Step 1: Replace the panel with a full-height column**

Root: `flex h-full min-h-0 flex-col` (no border/card — the page is the surface).
Scroll area: `flex-1 overflow-y-auto` wrapping `mx-auto w-full max-w-3xl px-4`.
Keep the auto-scroll `useEffect` on `[messages, quoteResult]`.

- [ ] **Step 2: Welcome state**

When `messages.length <= 1` render (instead of the message list):

```tsx
const STARTER_PROMPTS = [
  { title: "Start an auto quote", hint: "Five quick details, instant premium", prompt: "I want a quote for auto insurance" },
  { title: "What does comprehensive include?", hint: "Answers from the policy knowledge base", prompt: "What does comprehensive coverage include?" },
  { title: "Home insurance quote", hint: "Coverage for your property in minutes", prompt: "I want a home insurance quote" },
  { title: "Compare pricing tiers", hint: "Basic, standard, and premium side by side", prompt: "Compare the pricing tiers" }
];
```

Centered: `IvoryLogo` 56px, `font-[family-name:var(--font-display)] text-4xl`
"How can we help today?", muted subline, `grid gap-3 sm:grid-cols-2` starter
cards (`rounded-xl border border-line bg-white p-4 text-left hover:shadow-md`).
Card click calls `onQuickPrompt(prompt)` — **the handler must send, not prefill**
(App change in Task 6).

- [ ] **Step 3: Pill composer**

```tsx
<form
  className="mx-auto w-full max-w-3xl px-4 pb-5"
  onSubmit={(e) => { e.preventDefault(); onSend(); }}
>
  {quickReplies}
  <div className="flex items-end gap-2 rounded-[28px] border border-line bg-white px-4 py-2.5 shadow-sm transition focus-within:border-teal focus-within:ring-4 focus-within:ring-teal/10">
    <label className="sr-only" htmlFor="message-input">Message Ivory</label>
    <textarea
      id="message-input"
      rows={1}
      className="max-h-40 flex-1 resize-none bg-transparent py-1.5 text-base outline-none placeholder:text-muted/60"
      value={draft}
      onChange={(e) => onDraftChange(e.target.value)}
      onKeyDown={(e) => {
        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onSend(); }
      }}
      placeholder="Message Ivory…"
    />
    {isSending ? (
      <button type="button" onClick={onStop} aria-label="Stop generating"
        className="flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-full bg-ink text-white transition-colors hover:bg-black">
        {/* square stop SVG, 12px */}
      </button>
    ) : (
      <button type="submit" aria-label="Send message" disabled={!draft.trim() || isResetting}
        className="flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-full bg-teal text-white transition-colors hover:bg-teal-hover disabled:cursor-not-allowed disabled:bg-line">
        {/* arrow-up SVG */}
      </button>
    )}
  </div>
  <p className="mt-2 text-center text-xs text-muted/70">
    Ivory is an AI assistant — quotes are estimates, not final offers.
  </p>
</form>
```

Auto-grow: `onChange` also sets `e.target.style.height = "auto"; e.target.style.height = e.target.scrollHeight + "px"` (cap via the `max-h-40` class).

- [ ] **Step 4: Quick-reply chips**

New prop `hasQuoteResult: boolean`. When true and not sending, render above the
composer: `Accept` / `Adjust details` / `Start over` as
`rounded-full border border-line bg-white px-3 py-1.5 text-[13px] text-muted hover:border-teal hover:text-teal cursor-pointer`,
each calling `onQuickPrompt` with the literal text (`"accept"`, `"adjust"`,
`"restart"` — the backend's expected intents).

- [ ] **Step 5: Keep** error banner (`role="alert"`, restyle to
`border-rose-200 bg-rose-50`), typing indicator block (`role="status"
aria-live="polite"`, restyled flat next to an avatar). Delete the old header row
("Conversation / New / Reset" — New moves to sidebar, Reset becomes header icon in Task 6).

New props summary: add `hasQuoteResult`; remove `sessionLabel`, `statusText`,
`quoteResult` (no longer rendered here — auto-scroll keys on `messages` only).

- [ ] **Step 6: Typecheck + commit** (after Task 6 makes App.tsx match, if inline)

```bash
git add frontend/src/components/ChatWindow.tsx
git commit -m "ui: centered conversation column, welcome state, pill composer"
```

---

### Task 6: `App.tsx` shell — sidebar + slim header + progress

**Files:**
- Modify: `frontend/src/App.tsx` (workspace return-branch only; login branch untouched)

- [ ] **Step 1: Derive header state from the snapshot (pure helpers above component)**

```tsx
const STEP_PROGRESS: Record<string, number> = {
  identify: 0.15,
  collect: 0.5,
  collect_details: 0.5,
  validate: 0.75,
  confirm: 1,
  quote: 1
};

function flowChipLabel(snapshot: SessionSnapshot | null): string | null {
  if (snapshot?.mode !== "transactional") return null;
  const product = snapshot.insurance_type
    ? `${snapshot.insurance_type} quote`
    : "Quote";
  const step = snapshot.quote_step
    ? snapshot.quote_step.replace(/_/g, " ")
    : "in progress";
  return `${product} · ${step}`;
}

function progressFraction(snapshot: SessionSnapshot | null): number | null {
  if (snapshot?.mode !== "transactional") return null;
  return STEP_PROGRESS[snapshot.quote_step ?? ""] ?? 0.3;
}
```

- [ ] **Step 2: New shell layout**

```
<main flex h-svh bg-ivory>
  <Sidebar … hidden lg:flex, width 264/64 by `sidebarOpen` />
  <mobile drawer: existing overlay pattern, renders <Sidebar collapsed={false}> at w-[min(88vw,300px)]>
  <div flex-1 flex flex-col min-w-0>
    <header flex items-center justify-between border-b border-line/70 px-4 sm:px-6 py-3>
      left: mobile menu button (lg:hidden) + conversation title (first user
            message preview, truncated, fallback "Ivory")
      right: [flow chip if flowChipLabel] [status chip: dot + text] [reset icon button → chat.resetSession]
    </header>
    {progressFraction !== null && (
      <div className="h-[3px] w-full bg-soft">
        <div className="h-full rounded-r-full bg-teal transition-all duration-300"
             style={{ width: `${progressFraction * 100}%` }} />
      </div>
    )}
    <ChatWindow … flex-1 min-h-0 />
  </div>
</main>
```

Status chip text: `isSending ? "Thinking…" : snapshot?.has_quote_result ?
"Quote ready" : snapshot?.mode === "transactional" ? "Collecting details" :
"Knowledge mode"`; dot `bg-teal`, `animate-pulse` while sending.

- [ ] **Step 3: Wire the callbacks**

- `onQuickPrompt={(prompt) => void chat.sendMessage(prompt)}` — sends immediately.
- `hasQuoteResult={Boolean(chat.sessionSnapshot?.has_quote_result)}`.
- Sidebar: `onNewConversation={chat.createNewSession}`,
  `onRestoreSession={chat.restoreSession}`, `onLogout={handleLogout}`,
  `userLabel={demoUsernameHint || "Workspace"}`.
- Delete: `startNewQuote`, `StatePill`, `NavItem`, `formatLabel` if now unused,
  both `QuoteCard variant="spotlight"` blocks, the "Current state" / "Local
  history" sidebar sections (absorbed by Sidebar), and unused imports.

- [ ] **Step 4: Typecheck**

Run: `cd frontend && npx tsc --noEmit` → clean, zero unused-symbol errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/
git commit -m "ui: conversation-first shell — sidebar, slim header, progress bar"
```

---

### Task 7: Verify end-to-end, ship

- [ ] **Step 1:** `cd frontend && npx tsc --noEmit` → clean.
- [ ] **Step 2:** Backend suite untouched-proof: `backend/.venv/bin/python -m pytest tests/ -q` → `41 passed`.
- [ ] **Step 3:** Playwright (dev server on :3000): demo login → screenshot welcome
  (1280×800) → click "Start an auto quote" starter card → wait for assistant
  reply → screenshot conversation → set viewport 375×812 → screenshot mobile.
  Compare against `docs/design/mockups/ivory-modern-chat.html` screenshots.
- [ ] **Step 4:** Fix visual deltas found in Step 3 (spacing, truncation, chips), re-shoot.
- [ ] **Step 5:** Commit + push:

```bash
git add -A && git commit -m "ui: modern conversation-first redesign per spec"
git push origin HEAD:main && git push shieldbase HEAD:feat/deterministic-rearchitecture
```

---

## Self-review

- Spec coverage: §5.1→Task 2, §5.2→Task 6, §5.3→Task 5, §5.4→Task 4, §5.5→Task 1, §6→embedded in tasks + Task 7, acceptance criteria→Task 7. ✓
- No placeholders: all code shown or pointed at an existing in-repo artifact (mockup HTML) for exact classes. ✓
- Type consistency: `ChatWindow` prop changes (add `hasQuoteResult`, drop `sessionLabel`/`statusText`/`quoteResult`) match Task 6 wiring; `QuoteCard` drops `variant` and Task 6 deletes its usages. ✓
