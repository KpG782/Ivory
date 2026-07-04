# Layman Mental Model Flow

This document is a plain-English explanation of how Ivory works, so you can explain it clearly in a demo, interview, or walkthrough without sounding too technical.

## The One-Sentence Explanation

Ivory is a dental front-desk chatbot that can do two things in one conversation:

- answer dental and clinic questions
- guide a patient through setting up a visit step by step

The important part is that it can switch between those two without losing track of where the patient is.

## The Simplest Mental Model

Think of Ivory like a smart front-desk assistant at a dental clinic.

It can do two jobs:

1. answer questions like:
   - What should I do about a toothache?
   - What happens during a routine cleaning?
2. help collect visit details like:
   - What's the patient's full name?
   - What year was your last dental visit?
   - On a scale of 0 to 10, how bad is the pain?

If the patient interrupts the booking to ask a question, the assistant answers it and then goes right back to the next missing visit detail.

That is the main behavior this project is built around.

## The Core Idea To Say Out Loud

The system is not just a chatbot that generates text.

It is really two systems working together:

- a question-answering system
- a step-by-step intake workflow

The backend decides which one should handle the user’s message.

## The Two Modes

### 1. Knowledge mode

This is for normal dental and clinic questions.

Example:

- user asks: `What does a routine cleaning include?`
- assistant looks at the knowledge base
- assistant returns an answer grounded in the stored markdown documents

### 2. Intake mode

This is for collecting details needed to set up a visit.

Example:

- user says: `I'd like to book a cleaning`
- assistant starts asking the required intake questions
- it validates each answer one step at a time
- once everything is complete, it calculates a visit estimate

## The Best Non-Technical Analogy

Use this if someone is not technical:

Ivory works like a receptionist with a checklist.

- If you ask a general question, it gives you an answer.
- If you ask to book a visit, it pulls out the right checklist (cleaning, emergency, or cosmetic).
- If you interrupt with another question, it answers you without throwing away the checklist.
- Then it goes back to the exact line it was on.

That is why the app feels conversational, but still behaves reliably like a form when it needs to.

## The Real User Journey

Here is the easiest way to explain a real conversation flow:

1. The patient opens the app and types a message.
2. The system checks what the patient is trying to do.
3. If it is a dental question, it answers from the knowledge base.
4. If it is a booking request, it starts a structured intake flow.
5. If the patient interrupts the intake with a question, it answers the question.
6. Then it resumes the intake from the exact missing field.
7. When all intake fields are collected, it calculates an estimated cost range.
8. The patient can then accept, adjust, or restart.
9. On accept, the front-desk chores run: a lead is saved to the clinic CRM, an appointment request is sent, and a confirmation email is drafted. Without real service keys, each of those honestly reports "demo mode" instead.

## What Makes It Better Than A Basic Chatbot

A basic chatbot can answer questions, but it often loses track of structured tasks.

Ivory is stronger because:

- it remembers the intake step
- it validates patient input
- it keeps intake data on the backend
- it does not rely on the AI model to do the estimate math
- it can resume after interruptions

The short version:

It behaves like a chatbot when answering questions, but like a workflow engine when setting up a visit.

## How To Explain The Knowledge Base

You can say:

The chatbot answers dental questions using a set of markdown files that act like its handbook.

Those files contain:

- a clinic overview and FAQ (hours, parking, cancellation policy)
- service explainers for cleanings, emergencies, and cosmetic treatments
- pricing, insurance, and payment guidance
- health education about tooth decay, gum disease, children's dentistry, and oral cancer screening
- aftercare scenarios

The health content is grounded in public government sources (NIDCR and CDC), and every file names its sources. So when someone asks a question, the assistant is not supposed to invent an answer from nowhere. It is supposed to answer based on that stored reference material — and it never gives medical advice or a diagnosis.

## How To Explain The Estimate Logic

You can say:

The estimate is not invented by the AI.

The AI helps with conversation, but the actual estimate uses fixed business rules.

That means:

- the required fields are predefined
- each answer is validated
- the final cost range is calculated in code (a simple fee schedule)

Every estimate is labeled as educational — not a diagnosis and not a final price. This makes the intake flow more reliable and easier to defend in a demo.

## How To Explain Why The Backend Matters

You can say:

The backend is the memory and decision-maker.

It stores:

- what mode the chat is in
- which service the patient picked
- what intake step they are on
- what information has already been collected
- whether a visit estimate already exists

So even if the chat feels conversational, the important workflow state is controlled by the backend, not guessed by the frontend.

## How To Explain The Frontend

You can say:

The frontend is mainly the presentation layer.

It:

- shows the streaming answer
- displays the current intake state
- shows the visit card with the estimate range
- lets the user reset, adjust, or continue
- allows exporting visit details as JSON or CSV

The frontend does not decide the intake logic. It reflects what the backend sends back.

## The Most Important “Why”

If someone asks why the architecture is built this way, the best answer is:

Because the problem has two different kinds of work:

- open-ended question answering
- structured transaction handling

If you treat both like normal chat, the app becomes unreliable.

If you separate them but keep them in one session, the app becomes much more usable.

That is the main design decision.

## Short Interview Answer

If you only have 20 to 30 seconds, say this:

Ivory is a hybrid dental front-desk assistant. It can answer dental questions from a knowledge base, and it can also run a structured intake workflow for cleanings, emergency visits, and cosmetic consultations. The backend keeps the intake state, so if a patient interrupts the flow with a question, the assistant answers it and then resumes from the exact next missing field. The estimate itself is deterministic and calculated in code, not invented by the LLM — and when the patient accepts, the front-desk actions (CRM lead, booking request, confirmation email) run automatically, safely falling back to demo mode without keys.

## Slightly Longer Demo Answer

If you have around one minute, say this:

The easiest way to think about Ivory is as two systems in one chat. One part handles dental questions using a markdown-based knowledge base grounded in public health sources. The other part handles visit intake like a guided checklist. The backend decides which path to use for each message. If the patient starts a booking, the system collects the required fields step by step and validates each one — a made-up name like "i like dogs" or a pain level of -2 gets rejected and re-asked. If the patient interrupts with a dental question, the assistant answers it but keeps the intake state intact, then resumes the exact next step. Once all the data is collected, the cost range is calculated with deterministic rules in code, and accepting the visit triggers the front-desk actions. So the app feels conversational, but the transaction part remains stable and predictable.

## Best Phrases To Reuse

These are safe phrases to repeat in a demo:

- “It is a hybrid chat and workflow system.”
- “The backend is the source of truth.”
- “The intake flow is structured, not improvised.”
- “The LLM helps with language, not estimate math.”
- “Patients can interrupt the flow without losing progress.”
- “It answers like a chatbot, but behaves like a guided form when needed.”
- “Estimates are educational — never a diagnosis or a final price.”

## What To Avoid Saying

Avoid vague answers like:

- “It’s just an AI dental bot.”
- “The model figures everything out.”
- “The frontend handles the flow.”
- “The estimate is generated by AI.”

Those descriptions make the system sound weaker or less controlled than it really is.

## Good Q&A Prep

### If asked: “What is special about this app?”

Say:

The key part is not just that it answers questions. The key part is that it can pause and resume a structured intake flow without losing state.

### If asked: “Why not just use one prompt?”

Say:

Because open-ended chat and step-by-step transactions have different reliability needs. A single free-form prompt is much more likely to lose track of structured progress.

### If asked: “Why is the estimate deterministic?”

Say:

Because a cost range a patient will see should be predictable, testable, and easier to validate. The AI handles conversation, but the fee logic lives in code.

### If asked: “What does the knowledge base do?”

Say:

It provides the factual grounding for dental questions, so the assistant has a defined source of information instead of relying only on model memory — and it keeps the assistant educational rather than diagnostic.

### If asked: “What does the frontend do?”

Say:

It presents the conversation, current intake state, and results. It is the interface layer, not the workflow brain.

### If asked: “What happens on accept?”

Say:

Accept is the only moment external systems are touched: the clinic CRM gets a lead, the scheduling system gets a booking request, and a confirmation email is drafted. Without keys configured, each action safely reports demo mode instead of calling out — and a failure in one becomes an honest line in the reply, never a crash.

## Final Mental Shortcut

If you forget everything else, remember this:

Ivory is a chatbot with a checklist brain.

- handbook for questions
- checklist for visits
- memory on the backend
- deterministic estimate at the end
- front-desk actions only on accept
