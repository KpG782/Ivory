# Knowledge Base Quick Reference

This document is a fast map of the markdown files in `backend/knowledge_base/`.

It explains:

- the general format used across the knowledge base
- what kind of information each markdown contains
- which files are product definitions, workflow guidance, or scenario support

## Folder Purpose

The `backend/knowledge_base/` folder contains the grounded content used by the chatbot for insurance Q&A and quote-related explanations.

The files are short, practical markdown documents written for:

- RAG retrieval
- quote-flow explanation
- clarification of coverage, exclusions, limits, and examples
- assistant behavior guidance

## Common Markdown Format

Most files follow a simple pattern:

1. `# Title`
2. Short introductory paragraph explaining the topic
3. `##` sections for major knowledge blocks
4. Bullet lists for concrete facts, examples, or supported user questions

## Common Section Patterns

Several files reuse one of these formats.

### Product definition format

Usually contains:

- `## What it can cover`
- `## Quote inputs`
- `## Pricing factors`
- `## Common exclusions and limits`
- `## Helpful assistant answers`

Used by:

- `02_auto_insurance.md`
- `03_home_insurance.md`
- `04_life_insurance.md`

### Reference / explainer format

Usually contains:

- topic definitions
- examples
- exclusions or limits
- assistant guidance
- common user questions

Used by:

- `05_pricing_tiers.md`
- `06_claims_process.md`
- `08_auto_coverage_levels_and_deductibles.md`
- `09_home_endorsements_and_limits.md`
- `10_life_underwriting_and_beneficiaries.md`
- `11_discounts_and_eligibility.md`
- `12_claim_scenarios_and_examples.md`

### FAQ format

Uses direct question headings:

- `## What types of insurance does Ivory offer?`
- `## Can I ask a question while I am getting a quote?`

Used by:

- `07_faq.md`

### Foundation / system guidance format

Defines the chatbot’s overall scope and expected behavior.

Used by:

- `01_company_overview.md`

## File-By-File Summary

## `01_company_overview.md`

### Purpose

Top-level definition of what Ivory is and how the assistant should behave.

### Main sections

- assistant behavior
- product coverage
- quote experience

### Knowledge type

- company-level overview
- assistant workflow expectations
- session/quote behavior guidance

### Why it matters

This is the broadest grounding file. It tells the assistant that it must support both Q&A and structured quote collection without losing quote state.

## `02_auto_insurance.md`

### Purpose

Core auto insurance product overview.

### Main sections

- what it can cover
- quote inputs
- pricing factors
- common exclusions and limits
- helpful assistant answers

### Knowledge type

- auto coverage basics
- required auto quote fields
- pricing influences
- common exclusions

## `03_home_insurance.md`

### Purpose

Core home insurance product overview.

### Main sections

- what it can cover
- quote inputs
- pricing factors
- common exclusions and limits
- helpful assistant answers

### Knowledge type

- home coverage basics
- home quote field requirements
- home exclusions like flood/earthquake

## `04_life_insurance.md`

### Purpose

Core life insurance product overview.

### Main sections

- what it can cover
- quote inputs
- pricing factors
- common exclusions and limits
- helpful assistant answers

### Knowledge type

- term-life basics
- life quote field requirements
- age, health, smoker, term, and amount factors

## `05_pricing_tiers.md`

### Purpose

Defines the simplified coverage tiers used by the quote flow.

### Main sections

- tier definitions
- basic
- standard
- comprehensive
- how tiers affect quotes
- assistant guidance

### Knowledge type

- quote-tier interpretation
- simple user-facing explanation of tier differences

### Why it matters

This file helps the bot explain what `basic`, `standard`, and `comprehensive` mean in plain language.

## `06_claims_process.md`

### Purpose

Explains the claims process across products.

### Main sections

- general flow
- auto claims
- home claims
- life claims
- assistant guidance

### Knowledge type

- claims steps
- documents and evidence examples
- safe language for claim discussions

## `07_faq.md`

### Purpose

Captures short direct answers to common assistant behavior and product-flow questions.

### Main sections

- what types of insurance are offered
- whether users can ask questions mid-quote
- what happens after invalid input
- whether users need to know the exact product first
- how quotes are estimated
- whether users can switch quotes
- what happens when the assistant does not know

### Knowledge type

- policy FAQ
- chatbot behavior FAQ
- quote workflow expectations

## `08_auto_coverage_levels_and_deductibles.md`

### Purpose

Detailed auto explainer focused on coverage tiers, comprehensive coverage, and deductibles.

### Main sections

- basic
- standard
- comprehensive
- what comprehensive means in auto insurance
- what a deductible means
- common user questions this document should support

### Knowledge type

- deeper auto clarification
- deductible explanation
- examples of what comprehensive includes

### Why it matters

This is one of the strongest retrieval sources for questions like:

- what does comprehensive cover
- does comprehensive cover theft
- what is a deductible

## `09_home_endorsements_and_limits.md`

### Purpose

Detailed home insurance explainer for limits, exclusions, optional add-ons, and deductibles.

### Main sections

- core home coverage areas
- common exclusions
- policy limits
- optional add-ons or endorsements
- deductible expectations
- common user questions this document should support

### Knowledge type

- home exclusions and limitations
- optional coverages
- deductible and sub-limit guidance

## `10_life_underwriting_and_beneficiaries.md`

### Purpose

Detailed life insurance explainer beyond the basic product file.

### Main sections

- what term life insurance does
- beneficiaries
- underwriting factors
- contestability and disclosure
- lapse risk
- common user questions this document should support

### Knowledge type

- beneficiary explanation
- underwriting basics
- lapse and disclosure guidance

## `11_discounts_and_eligibility.md`

### Purpose

Explains readiness, discounts, and safe eligibility framing.

### Main sections

- example discount themes
- auto quote readiness
- home quote readiness
- life quote readiness
- eligibility framing
- common user questions this document should support

### Knowledge type

- pre-quote preparation
- discount concepts
- safe wording around eligibility and approval

### Why it matters

This file is especially useful when the user asks:

- what do I need before starting a quote
- am I eligible
- do you offer discounts

## `12_claim_scenarios_and_examples.md`

### Purpose

Provides scenario-style explanations instead of abstract definitions.

### Main sections

- auto examples
- collision example
- comprehensive example
- liability example
- home examples
- life examples
- assistant behavior guidance
- common user questions this document should support

### Knowledge type

- scenario-based claim and coverage examples
- practical “would this be covered?” style grounding

## Quick Category Map

### Foundation

- `01_company_overview.md`

### Core product files

- `02_auto_insurance.md`
- `03_home_insurance.md`
- `04_life_insurance.md`

### Quote and pricing support

- `05_pricing_tiers.md`
- `11_discounts_and_eligibility.md`

### Claims support

- `06_claims_process.md`
- `12_claim_scenarios_and_examples.md`

### FAQ and workflow behavior

- `07_faq.md`
- `01_company_overview.md`

### Deep-dive explainers

- `08_auto_coverage_levels_and_deductibles.md`
- `09_home_endorsements_and_limits.md`
- `10_life_underwriting_and_beneficiaries.md`

## Overall Knowledge Design

The folder is organized in layers:

1. broad system and product grounding
2. quote input and pricing guidance
3. deeper coverage/exclusion explainers
4. claims and scenario examples
5. FAQ-style assistant behavior rules

This means the assistant can answer both:

- broad product questions
- workflow questions during quote collection
- scenario-based questions like `Would hail damage be collision or comprehensive?`

## Short Takeaway

If you want the fastest mental model:

- `01` = what the assistant is supposed to be
- `02-04` = the three main products
- `05` = quote tier meanings
- `06` = claims process
- `07` = FAQ behavior rules
- `08-10` = deeper product explainers
- `11` = discounts, eligibility, quote readiness
- `12` = example scenarios
