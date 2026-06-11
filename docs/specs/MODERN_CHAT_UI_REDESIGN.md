# Modern Chat UI Redesign — Design Spec

**Date:** 2026-06-11
**Status:** Approved (mockup reviewed: `docs/design/mockups/ivory-modern-chat.html`)
**Scope:** Frontend workspace only. Backend contracts, `useChat` hook API, and the
login screen are unchanged.

---

## 1. Goal

Replace the three-rail dashboard workspace with the conversation-first layout that
ChatGPT, Claude, and Intercom trained users to expect — so a first-time visitor
needs zero learning before using Ivory. At the same time, make the deterministic
state machine (Ivory's engineering differentiator) *visible* as UX instead of
hidden in a side panel.

## 2. Target audience

| Audience | Context | What they need |
|----------|---------|----------------|
| Portfolio reviewers (now) | Desktop, 2-minute scan | Instantly familiar layout; the state machine visibly doing its job; screenshots that demo well |
| End customers (insurance now, dental patients after migration) | Mobile-heavy, non-technical, all ages | Zero learning curve, 16px+ text, one obvious action at every moment, accessible AA+ |

Design rule derived from both: **every piece of chrome must justify itself; the
conversation is the interface.**

## 3. Research basis

- Convention analysis of ChatGPT / Claude / Intercom (the "five conventions":
  centered column, asymmetric messages, pill composer, history sidebar, status as chips).
- Ivory design system: `design-system/ivory/MASTER.md` (tokens, components,
  anti-patterns) — built with ui-ux-pro-max (Healthcare App category, Accessible &
  Ethical baseline).
- ui-ux-pro-max React stack guidance: label every input (`htmlFor`), manage focus,
  lazy state init, `aria-live` regions for streamed/dynamic content.
- Approved HTML mockup: `docs/design/mockups/ivory-modern-chat.html` (Screen 1
  welcome, Screen 2 active quote).

## 4. Information architecture

```
┌──────────┬──────────────────────────────────────────────┐
│ Sidebar  │ Header: title · [flow chip] · [status chip]  │
│          │ ── progress bar (transactional mode only) ── │
│ · Logo   │                                              │
│ · New    │           Conversation column                │
│   conv.  │           (max-w-3xl, centered)              │
│ · History│   assistant: flat text + avatar              │
│   Today/ │   user: teal bubble, right                   │
│   Yest./ │   quote: inline card in the thread           │
│   Older  │                                              │
│ · User + │   [quick-reply chips when flow expects one]  │
│   logout │   [ pill composer ............... (send) ]   │
│          │   disclaimer line                            │
└──────────┴──────────────────────────────────────────────┘
```

What the old right-rail/state-panel content becomes:

| Old location | New home |
|---|---|
| Mode / Step / Status panel | Header chips (`Auto quote · collecting`, status dot) + progress bar |
| Quote summary rail (`spotlight` QuoteCard) | Inline `QuoteCard` in the message thread (already exists as `embedded` variant) |
| Local history section | Sidebar conversation list, grouped Today / Yesterday / Older |
| "New quote" button | Sidebar "New conversation" + welcome-screen starter card |

## 5. Component specs (mapped to the existing `useChat` contract)

### 5.1 Sidebar (`Sidebar.tsx`, new)
- 264px expanded; collapses to 64px icon rail (desktop); overlay drawer on mobile
  (existing pattern, `lg:` breakpoint).
- Contents top→bottom: logo + serif wordmark, teal "New conversation" pill
  (`chat.createNewSession`), history list (`chat.savedSessions`, grouped by
  `updatedAt`: Today / Yesterday / Older; `chat.restoreSession` on click;
  truncated `preview` as label), footer user chip (`demo` initial +
  `NEXT_PUBLIC_AUTH_DEMO_USER` or "Workspace") with logout icon button.
- Empty history: one muted line, no empty cards.

### 5.2 Header (in `App.tsx`)
- Slim bar, `border-b`, no card chrome. Left: mobile menu button + current
  conversation title (first user message preview, fallback "Ivory").
- Right chips:
  - **Flow chip** (only when `sessionSnapshot.mode === "transactional"`):
    teal-tint pill, `{insurance_type} quote · {step label}` from
    `sessionSnapshot.quote_step`.
  - **Status chip**: white pill, teal dot, `Knowledge mode` /
    `Collecting details` / `Quote ready` derived from snapshot; pulses while
    `isSending`.
- **Progress bar**: 3px, under the header, only in transactional mode. Step →
  fraction mapping: identify 0.15, collect 0.5, validate 0.75, confirm/quote 1.0
  (coarse is fine — it communicates motion, not precision).

### 5.3 Conversation column (`ChatWindow.tsx`, rewritten)
- `max-w-3xl mx-auto`, vertical scroll on the column wrapper, auto-scroll to
  bottom on new messages (existing behavior preserved).
- **Welcome state** (when only the welcome message exists): centered Ivory icon,
  Playfair `text-4xl` "How can we help today?", subline, 2×2 starter cards
  (1-col on mobile). Cards call `onQuickPrompt` with their prompt and submit
  immediately (not just prefill — one click = one action).
- **Messages** (`MessageBubble.tsx`, restyled):
  - Assistant: flat — 28px Ivory avatar left, Markdown body `text-[15px]
    leading-7`, no card/border. Error kind: rose tint block. Streaming: existing
    TypingIndicator; `aria-live="polite"` stays.
  - User: right-aligned teal (`#0F766E`) bubble, white text, `rounded-2xl
    rounded-br-md`, `max-w-[75%]`.
  - Quote attached to a message renders `QuoteCard` inline under the text.
- **Composer**: pill container (`rounded-[28px]`, white, `border-line`,
  focus ring teal/10), auto-growing textarea (1 row min, ~6 max), circular teal
  send button with arrow icon inside the pill; Enter submits, Shift+Enter
  newline. While `isSending`: send button becomes Stop (square icon),
  `onStop` wired. Below: centered disclaimer line.
- **Quick-reply chips** above composer, contextual:
  - `has_quote_result` true → `Accept` / `Adjust details` / `Start over`
    (send those literal messages).
  - Welcome state → none (starter cards cover it).
- Error banner: unchanged behavior, restyled to tokens.

### 5.4 QuoteCard (`QuoteCard.tsx`, restyled, `embedded` only)
- White card, `border-line`, `rounded-xl`, `shadow-sm`; header row (title +
  coverage badge in teal tint), detail rows (muted label / medium value),
  premium row with serif teal figure, actions: existing export buttons (Copy
  JSON / Download JSON / CSV) restyled as small outline pills.
- The `spotlight` variant is no longer rendered (rail is gone); keep the prop
  accepted for compatibility, render nothing for it — actually: delete the
  variant and its usages in the same change. No dead code.

### 5.5 Tokens & typography (`globals.css`, `layout.tsx`)
- Fonts: Inter (`--font-body`) + Playfair Display (`--font-display`) via
  `next/font` — replaces Manrope + Space Grotesk.
- Tailwind `@theme` tokens replace gold/sand palette: `ivory #FAFAF9`,
  `ink #1C1917`, `muted #57534E`, `teal #0F766E / hover #115E59 / tint #CCFBF1`,
  `line #E7E5E4`, `soft #F5F5F4`. Page background: flat `#FAFAF9` (kill the
  radial gold gradients — anti-pattern: decorative wash).
- Playfair only: wordmark, welcome headline, premium figure. Inter everywhere else.

## 6. Accessibility & quality gates (from design system + stack research)

- Text ≥ 15px in conversation, ≥ 16px inputs (prevents iOS zoom). Contrast AA+
  (ink/ivory ≈ 16:1, white/teal ≈ 5.3:1).
- `aria-live="polite"` on the streaming region; `role="alert"` on errors (existing).
- Every input labeled (`htmlFor`/`sr-only`); focus rings visible (teal, 3px+);
  all interactive elements `cursor-pointer`, hover via color/shadow only (no
  layout-shifting transforms).
- `prefers-reduced-motion` respected (existing `ui-*` animation classes already
  gate on it — verify, don't regress).
- Responsive: 375 / 768 / 1024 / 1440. Mobile: sidebar = drawer, starter cards
  1-col, composer full-width.
- No emoji icons; inline SVG (stroke 2) consistent set.

## 7. Out of scope

- Login screen (already on-brand), quote-confirmation page (separate route,
  later pass), backend/API changes, dental-vertical copy (comes with the
  migration), resume-prompt callout styling (needs a backend marker to be
  reliable — noted as a follow-up, not styled by text-sniffing).

## 8. Acceptance criteria

1. Welcome screen matches mockup Screen 1 (sidebar, hero, 4 starter cards, pill composer).
2. Active quote flow shows: header flow chip + progress bar, teal user bubbles,
   flat assistant messages, inline quote card with actions, quick-reply chips.
3. One click on a starter card sends the message (no second click).
4. `tsc --noEmit` clean; all 41 backend tests untouched and green.
5. Playwright click-through: demo login → welcome → starter card → streamed
   reply renders in new layout at 1280×800 and 375×812.
