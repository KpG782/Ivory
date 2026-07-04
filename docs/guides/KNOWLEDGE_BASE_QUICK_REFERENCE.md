# Knowledge Base Quick Reference

This document is a fast map of the markdown files in `backend/knowledge_base/`.

It explains:

- the general format used across the knowledge base
- what kind of information each markdown contains
- which files are service explainers, clinic/workflow guidance, or health education

## Folder Purpose

The `backend/knowledge_base/` folder contains the grounded content used by the chatbot for dental Q&A and visit-estimate explanations.

The files are short, practical markdown documents written for:

- RAG retrieval
- intake-flow explanation
- clarification of services, pricing, insurance, and aftercare
- assistant behavior guidance

All health content is grounded in public-domain NIDCR and CDC material; clinic-specific content (hours, fees, policies) is fictional demo content for Ivory Dental Studio. ADA/MouthHealthy content is deliberately never used. Every file ends with a `Sources:` line naming its grounding.

## Common Markdown Format

Most files follow a simple pattern:

1. `# Title`
2. Short introductory paragraph explaining the topic
3. `##` sections for major knowledge blocks
4. Bullet lists for concrete facts, examples, or supported user questions
5. A closing `Sources:` line (NIDCR/CDC pages, or the fictional clinic handbook)

## Common Section Patterns

Several files reuse one of these formats.

### Service explainer format

Usually contains:

- what the visit or treatment involves
- when it is needed / how often
- prevention or care guidance
- a closing `## Booking ... with Ivory` section that ties the topic to the intake flow

Used by:

- `02_routine_checkups_and_cleanings.md`
- `03_dental_emergencies.md`
- `04_cosmetic_dentistry.md`

### Health education / explainer format

Usually contains:

- how a condition develops
- stages, symptoms, warning signs
- risk factors
- prevention and treatment at the clinic

Used by:

- `08_tooth_decay_and_cavities.md`
- `09_gum_disease.md`
- `10_children_and_family_dentistry.md`
- `11_oral_cancer_screening.md`
- `12_aftercare_scenarios.md`

### FAQ format

Uses direct question headings:

- `## I'm a new patient. What happens at my first visit?`
- `## How does booking through Ivory actually work?`

Used by:

- `07_faq.md`

### Foundation / system guidance format

Defines the clinic's overall scope and how the assistant should behave.

Used by:

- `01_clinic_overview.md`

## File-By-File Summary

## `01_clinic_overview.md`

### Purpose

Top-level definition of Ivory Dental Studio and how the assistant should behave.

### Main sections

- what dental services we offer
- hours and location
- our team
- our philosophy
- how booking works with Ivory
- accessibility and comfort

### Knowledge type

- clinic-level overview
- assistant workflow expectations
- the three services (cleaning, emergency, cosmetic) in plain language

### Why it matters

This is the broadest grounding file. It answers "what services do you offer" and tells the assistant that it supports both Q&A and structured visit intake without losing intake state.

## `02_routine_checkups_and_cleanings.md`

### Purpose

Core explainer for the cleaning service (routine exam & cleaning).

### Main sections

- what happens during a routine visit
- why plaque and tartar matter
- how often should you come in
- daily care between visits
- booking a cleaning at Ivory Dental Studio

### Knowledge type

- routine-visit basics (CDC/NIDCR grounded)
- recall-interval guidance
- home-care advice

## `03_dental_emergencies.md`

### Purpose

First-steps guidance for the emergency service.

### Main sections

- toothache
- chipped or broken tooth
- knocked-out permanent tooth
- swelling and possible infection
- lost filling or crown
- booking an emergency visit with Ivory

### Knowledge type

- urgent first-aid steps (NIDCR/CDC grounded)
- the four intake issue types (toothache, chipped tooth, swelling, lost filling) plus knocked-out tooth
- when to seek immediate care

### Why it matters

This is one of the strongest retrieval sources for questions like:

- what should I do about a toothache
- my tooth got knocked out
- my face is swelling

## `04_cosmetic_dentistry.md`

### Purpose

Core explainer for the cosmetic service.

### Main sections

- professional teeth whitening
- porcelain veneers
- clear aligners
- composite bonding
- choosing between options
- booking a cosmetic consultation with Ivory

### Knowledge type

- the four cosmetic treatments in the intake flow (whitening, veneers, aligners, bonding)
- trade-offs and sensitivity expectations

## `05_pricing_and_estimates.md`

### Purpose

Explains the fee schedule that the deterministic visit estimator implements.

### Main sections

- cleaning visits (routine exam & cleaning)
- emergency visits (urgent exam + X-ray)
- cosmetic treatments
- what estimates do and do not include
- why the math is deterministic

### Knowledge type

- base fees and the factors that move them (years since last visit, insurance status, issue type, pain level, treatment, budget band, timeline)
- estimate framing: educational, not a diagnosis or final price

### Why it matters

This file lets the bot explain a visit estimate in plain language and mirrors `services/visit_estimator.py`.

## `06_insurance_and_payment.md`

### Purpose

Explains insurance, self-pay, and payment options.

### Main sections

- dental insurance plans we accept
- how insurance affects your visit estimate
- what to bring if you are insured
- self-pay patients
- Ivory Smile Membership (for uninsured patients)
- payment methods and financing
- estimates, always before treatment

### Knowledge type

- insured vs self-pay framing used by the intake `insurance_status` field
- payment and financing concepts

## `07_faq.md`

### Purpose

Captures short direct answers to common clinic and assistant behavior questions.

### Main sections

- new-patient first visit
- what to bring / forms
- hours, evenings, weekends
- cancellation policy
- parking
- children
- dental anxiety
- emergencies
- how booking through Ivory works
- whether Ivory gives medical advice (it does not)

### Knowledge type

- clinic policy FAQ
- chatbot behavior FAQ
- intake workflow expectations

## `08_tooth_decay_and_cavities.md`

### Purpose

Health education explainer on decay and cavities.

### Main sections

- how decay happens
- stages and symptoms
- what raises your risk
- prevention
- how we treat decay at Ivory Dental Studio

### Knowledge type

- NIDCR/CDC-grounded decay education
- prevention guidance

## `09_gum_disease.md`

### Purpose

Health education explainer on gingivitis and periodontitis.

### Main sections

- the two stages (gingivitis; periodontitis)
- warning signs
- what raises your risk
- how gum disease is treated at Ivory Dental Studio
- prevention

### Knowledge type

- NIDCR-grounded gum disease education
- reversible vs managed framing

## `10_children_and_family_dentistry.md`

### Purpose

Family dentistry explainer for parents.

### Main sections

- the first dental visit
- why baby teeth matter
- fluoride: the daily protection
- dental sealants: protecting the chewing surfaces
- healthy habits for the whole family
- family visits at Ivory Dental Studio

### Knowledge type

- CDC-grounded children's oral health
- sealants and fluoride basics

### Why it matters

This file is especially useful when the user asks:

- when should my child first see a dentist
- what are sealants
- is fluoride safe

## `11_oral_cancer_screening.md`

### Purpose

Explains the oral cancer screening included in routine exams.

### Main sections

- what oral cancer is
- who is at higher risk
- what the screening involves
- signs and symptoms to take seriously
- lowering your risk

### Knowledge type

- NIDCR-grounded screening education
- risk factors and warning signs

## `12_aftercare_scenarios.md`

### Purpose

Provides scenario-style aftercare guidance instead of abstract definitions.

### Main sections

- after a tooth extraction
- after teeth whitening
- after a filling or crown
- tooth sensitivity in general
- when in doubt

### Knowledge type

- practical "what do I do now?" style grounding
- post-treatment care and when to call the clinic

## Quick Category Map

### Foundation

- `01_clinic_overview.md`

### Core service files

- `02_routine_checkups_and_cleanings.md`
- `03_dental_emergencies.md`
- `04_cosmetic_dentistry.md`

### Pricing and payment support

- `05_pricing_and_estimates.md`
- `06_insurance_and_payment.md`

### FAQ and workflow behavior

- `07_faq.md`
- `01_clinic_overview.md`

### Health education deep-dives

- `08_tooth_decay_and_cavities.md`
- `09_gum_disease.md`
- `10_children_and_family_dentistry.md`
- `11_oral_cancer_screening.md`

### Aftercare scenarios

- `12_aftercare_scenarios.md`

## Overall Knowledge Design

The folder is organized in layers:

1. broad clinic and service grounding
2. pricing, insurance, and estimate guidance
3. deeper health-education explainers
4. aftercare and scenario examples
5. FAQ-style assistant behavior rules

This means the assistant can answer both:

- broad service questions
- workflow questions during intake collection
- scenario-based questions like `My crown fell out — what do I do until my visit?`

## Short Takeaway

If you want the fastest mental model:

- `01` = what the clinic and assistant are supposed to be
- `02-04` = the three services (cleaning, emergency, cosmetic)
- `05` = the fee schedule behind the estimator
- `06` = insurance and payment
- `07` = FAQ behavior rules
- `08-11` = health-education explainers (decay, gums, kids, screening)
- `12` = aftercare scenarios
