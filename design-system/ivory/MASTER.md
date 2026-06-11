# Ivory — Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/ivory/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** Ivory — the AI front desk for dental clinics
**Generated:** 2026-06-11 (ui-ux-pro-max base + Ivory brand customization)
**Category:** Healthcare App
**Brand guide:** see `docs/branding/IVORY_BRAND.md`

---

## Global Rules

### Color Palette

Warm ivory neutrals with a single deep-teal accent. Mostly neutral, one accent —
Apple-style restraint. No cyan washes, no AI purple gradients.

| Role | Hex | CSS Variable | Tailwind |
|------|-----|--------------|----------|
| Background (Ivory) | `#FAFAF9` | `--color-background` | `stone-50` |
| Surface (cards) | `#FFFFFF` | `--color-surface` | `white` |
| Surface soft | `#F5F5F4` | `--color-surface-soft` | `stone-100` |
| Border | `#E7E5E4` | `--color-border` | `stone-200` |
| Text (Ink) | `#1C1917` | `--color-text` | `stone-900` |
| Text muted | `#57534E` | `--color-text-muted` | `stone-600` |
| Primary / CTA (Deep Teal) | `#0F766E` | `--color-primary` | `teal-700` |
| Primary hover | `#115E59` | `--color-primary-hover` | `teal-800` |
| Accent tint (chips, highlights) | `#CCFBF1` | `--color-accent-tint` | `teal-100` |
| Gold (sparingly: ratings, premium badge) | `#CA8A04` | `--color-gold` | `yellow-600` |

**Contrast (verified intent):** Ink on Ivory ≈ 16:1 (AAA). Muted on Ivory ≈ 7:1 (AAA).
White on Deep Teal ≈ 5.3:1 (AA — buttons). Deep Teal on Ivory ≈ 5.5:1 (AA — links).

### Typography

**Pairing:** "Classic Elegant" — Playfair Display + Inter.

- **Wordmark + hero headlines (h1 only):** Playfair Display
- **Everything else (h2–h6, body, UI):** Inter
- **Mood:** timeless, premium, calm, clinical-clean, trustworthy

**Google Fonts:** [Playfair Display + Inter](https://fonts.google.com/share?selection.family=Inter:wght@300;400;500;600;700|Playfair+Display:wght@400;500;600;700)

**CSS Import:**
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@400;500;600;700&display=swap');
```

**Tailwind config:**
```js
fontFamily: { serif: ['Playfair Display', 'serif'], sans: ['Inter', 'sans-serif'] }
```

**Rule:** Playfair is reserved for the brand moment (wordmark, hero line). If serif
starts appearing in buttons, labels, or chat bubbles, it's wrong — pull it back.

### Spacing Variables

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | `4px` / `0.25rem` | Tight gaps |
| `--space-sm` | `8px` / `0.5rem` | Icon gaps, inline spacing |
| `--space-md` | `16px` / `1rem` | Standard padding |
| `--space-lg` | `24px` / `1.5rem` | Section padding |
| `--space-xl` | `32px` / `2rem` | Large gaps |
| `--space-2xl` | `48px` / `3rem` | Section margins |
| `--space-3xl` | `64px` / `4rem` | Hero padding |

### Shadow Depths

Shadows stay soft and warm-neutral — Ivory is a calm brand, not a floaty one.

| Level | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 1px 2px rgba(28,25,23,0.05)` | Subtle lift |
| `--shadow-md` | `0 4px 6px rgba(28,25,23,0.08)` | Cards, buttons |
| `--shadow-lg` | `0 10px 15px rgba(28,25,23,0.08)` | Modals, dropdowns |
| `--shadow-xl` | `0 20px 25px rgba(28,25,23,0.12)` | Hero images, featured cards |

---

## Component Specs

### Buttons

```css
/* Primary Button */
.btn-primary {
  background: #0F766E;
  color: #FFFFFF;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: background-color 200ms ease;
  cursor: pointer;
}

.btn-primary:hover {
  background: #115E59; /* color shift, not opacity/scale — no layout shift */
}

/* Secondary Button */
.btn-secondary {
  background: transparent;
  color: #0F766E;
  border: 2px solid #0F766E;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: background-color 200ms ease, color 200ms ease;
  cursor: pointer;
}

.btn-secondary:hover {
  background: #CCFBF1;
}
```

### Cards

```css
.card {
  background: #FFFFFF;
  border: 1px solid #E7E5E4;
  border-radius: 12px;
  padding: 24px;
  box-shadow: var(--shadow-sm);
  transition: box-shadow 200ms ease;
}

.card:hover {
  box-shadow: var(--shadow-md);
}
```

### Inputs

```css
.input {
  background: #FFFFFF;
  padding: 12px 16px;
  border: 1px solid #E7E5E4;
  border-radius: 8px;
  font-size: 16px;
  color: #1C1917;
  transition: border-color 200ms ease, box-shadow 200ms ease;
}

.input:focus {
  border-color: #0F766E;
  outline: none;
  box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.15);
}
```

### Modals

```css
.modal-overlay {
  background: rgba(28, 25, 23, 0.5);
  backdrop-filter: blur(4px);
}

.modal {
  background: #FFFFFF;
  border-radius: 16px;
  padding: 32px;
  box-shadow: var(--shadow-xl);
  max-width: 500px;
  width: 90%;
}
```

### Chat (product-specific)

```css
/* Agent bubble — Ivory speaks on soft surface */
.bubble-agent {
  background: #F5F5F4;
  color: #1C1917;
  border-radius: 16px 16px 16px 4px;
  padding: 12px 16px;
}

/* Patient bubble — deep teal, white text */
.bubble-user {
  background: #0F766E;
  color: #FFFFFF;
  border-radius: 16px 16px 4px 16px;
  padding: 12px 16px;
}
```

---

## Style Guidelines

**Style:** Accessible & Ethical (WCAG-first) over a Soft-Minimal premium base

**Keywords:** High contrast, large text (16px+), keyboard navigation, screen reader
friendly, WCAG compliant, visible focus states, semantic HTML, generous whitespace

**Key Effects:** Clear focus rings (3-4px), ARIA labels, skip links, responsive
design, reduced motion, 44x44px touch targets

### Page Pattern

**Pattern Name:** Minimal Single Column

- **Conversion Strategy:** Single CTA focus. Large typography. Lots of whitespace. No nav clutter. Mobile-first.
- **CTA Placement:** Center, large CTA button
- **Section Order:** 1. Hero headline (Playfair), 2. Short description, 3. Benefit bullets (3 max), 4. CTA, 5. Footer

---

## Anti-Patterns (Do NOT Use)

- ❌ Bright neon colors
- ❌ Motion-heavy animations
- ❌ AI purple/pink gradients
- ❌ Cyan/blue "medical SaaS" washes — Ivory is warm-neutral, not cold-blue
- ❌ Tooth clip-art, sparkle emojis, cartoon mascots

### Additional Forbidden Patterns

- ❌ **Emojis as icons** — Use SVG icons (Heroicons, Lucide, Simple Icons)
- ❌ **Missing cursor:pointer** — All clickable elements must have cursor:pointer
- ❌ **Layout-shifting hovers** — Avoid scale transforms that shift layout
- ❌ **Low contrast text** — Maintain 4.5:1 minimum contrast ratio
- ❌ **Instant state changes** — Always use transitions (150-300ms)
- ❌ **Invisible focus states** — Focus states must be visible for a11y

---

## Pre-Delivery Checklist

Before delivering any UI code, verify:

- [ ] No emojis used as icons (use SVG instead)
- [ ] All icons from consistent icon set (Heroicons/Lucide)
- [ ] `cursor-pointer` on all clickable elements
- [ ] Hover states with smooth transitions (150-300ms)
- [ ] Light mode: text contrast 4.5:1 minimum
- [ ] Focus states visible for keyboard navigation
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px
- [ ] No content hidden behind fixed navbars
- [ ] No horizontal scroll on mobile
- [ ] Playfair Display only in wordmark + h1; Inter everywhere else
