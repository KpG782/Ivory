# Ivory — Brand Guide

> The AI front desk for dental clinics.
> Companion file: `design-system/ivory/MASTER.md` (tokens, components, checklists).

---

## 1. The Name

**Ivory** is the classic word for teeth — calm, timeless, premium. It follows the
Apple naming model: one common word everyone can spell, say, and remember, with no
"AI", "-ly", or "Dent-" jargon bolted on.

- Collision check (2026-06-11): no major dental-tech product named Ivory.
  (We dropped Grin and Pearl — Get-Grin and Pearl AI are existing dental-tech companies.)
- Domains: bare `ivory.com/.ai` are registered (dictionary word — expected).
  Use a modifier domain or subdomain; `ivory-desk.vercel.app` style is fine for portfolio.

## 2. One-liner & Taglines

**One-liner (product):**
> Ivory answers patient questions, captures every lead, and books the appointment — while your team stays chairside.

**Taglines (pick per context):**
- *"The front desk that never sleeps."* — primary
- *"Every patient, answered."* — short/hero alt
- *"You handle the teeth. Ivory handles the desk."* — playful/demo

## 3. Brand Personality

A great receptionist: **calm, warm, precise.** Never rushed, never slangy, never
robotic. Ivory is quietly competent — it doesn't celebrate itself, it just gets the
patient booked.

| Trait | In practice |
|-------|-------------|
| Calm | Short sentences. No exclamation marks in UI chrome. One CTA per screen. |
| Warm | Uses the patient's name once captured. "We've saved your spot." |
| Precise | Concrete confirmations: date, time, clinic name — never vague "you're all set!" alone. |

## 4. Voice & Microcopy

- Sentence case everywhere (headings, buttons). Never ALL CAPS.
- Confirmations state the facts: *"Booked. Maria's confirmation is on its way to maria@email.com."*
- Errors are owned and actionable: *"That time was just taken. The next opening is Tuesday 2:30 PM — want it?"*
- Health answers cite their source (NIDCR / CDC) and never diagnose:
  *"For anything urgent, call the clinic directly."*
- The agent says "I" sparingly; the brand says "Ivory" in marketing, "we" in product.

## 5. Visual Identity (summary — tokens live in MASTER.md)

- **Canvas:** warm ivory (`#FAFAF9`), white cards, stone borders. Not cold blue, not clinical white.
- **One accent:** deep teal (`#0F766E`) for every primary action. Gold (`#CA8A04`) only for ratings/premium badges.
- **Type:** Playfair Display for the wordmark + hero line only; Inter for everything else.
- **Imagery:** real clinic photography or quiet abstract texture. No tooth clip-art, no mascots, no AI-purple gradients.

## 6. Logo Direction

- **Wordmark:** "Ivory" set in Playfair Display, Ink (`#1C1917`) on Ivory (`#FAFAF9`), generous letterspacing on the capital I.
- **App icon:** rounded square, ivory background, serif "I" in deep teal. Optional refinement: the dot of an "i" rendered as a subtle tooth-crown silhouette — only if it stays abstract.
- **Don't:** add gradients, sparkles, teeth illustrations, or "AI" badges to the mark.

## 7. Naming in the Stack

| Context | Name |
|---------|------|
| Product / UI / README | Ivory |
| Repo (new origin) | `ivory` or `ivory-front-desk` |
| Python package | `ivory` |
| Agent persona in chat | "Ivory" (the clinic's assistant — not a human pretender; discloses it's an AI when asked) |

## 8. Provenance

Brand developed 2026-06-11 from the insurance-chatbot rebrand research
(`docs/RESEARCH_PROMPTS.md`, `docs/DATASET_RESEARCH_DENTAL.md`), using
ui-ux-pro-max design-system generation (Healthcare App category, "Accessible &
Ethical" style baseline, "Classic Elegant" typography pairing, Luxury/Premium
palette direction) and a five-candidate naming exploration (Enamel, Inlay, Molara,
Chairside, Cusp → simplified round: Floss, Mint, Swish, **Ivory**, Polish).
