# Layman Mental Model Flow

This document is a plain-English explanation of how Ivory works, so you can explain it clearly in a demo, interview, or walkthrough without sounding too technical.

## The One-Sentence Explanation

Ivory is an insurance chatbot that can do two things in one conversation:

- answer insurance questions
- guide a user through getting a quote step by step

The important part is that it can switch between those two without losing track of where the user is.

## The Simplest Mental Model

Think of Ivory like a smart front-desk assistant at an insurance office.

It can do two jobs:

1. answer questions like:
   - What does comprehensive coverage mean?
   - Does home insurance cover floods?
2. help collect quote details like:
   - What year is your car?
   - What is the property value?
   - Are you a smoker?

If the customer interrupts the quote to ask a question, the assistant answers it and then goes right back to the next missing quote detail.

That is the main behavior this project is built around.

## The Core Idea To Say Out Loud

The system is not just a chatbot that generates text.

It is really two systems working together:

- a question-answering system
- a step-by-step quote workflow

The backend decides which one should handle the user’s message.

## The Two Modes

### 1. Knowledge mode

This is for normal insurance questions.

Example:

- user asks: `What does comprehensive coverage include?`
- assistant looks at the knowledge base
- assistant returns an answer grounded in the stored markdown documents

### 2. Quote mode

This is for collecting details needed to build a quote.

Example:

- user says: `I want a quote for auto insurance`
- assistant starts asking the required quote questions
- it validates each answer one step at a time
- once everything is complete, it calculates a quote

## The Best Non-Technical Analogy

Use this if someone is not technical:

Ivory works like a receptionist with a checklist.

- If you ask a general question, it gives you an answer.
- If you ask for a quote, it pulls out the right checklist.
- If you interrupt with another question, it answers you without throwing away the checklist.
- Then it goes back to the exact line it was on.

That is why the app feels conversational, but still behaves reliably like a form when it needs to.

## The Real User Journey

Here is the easiest way to explain a real conversation flow:

1. The user opens the app and types a message.
2. The system checks what the user is trying to do.
3. If it is a product question, it answers from the knowledge base.
4. If it is a quote request, it starts a structured quote flow.
5. If the user interrupts the quote with a question, it answers the question.
6. Then it resumes the quote from the exact missing field.
7. When all quote fields are collected, it calculates a premium.
8. The user can then accept, adjust, or restart.

## What Makes It Better Than A Basic Chatbot

A basic chatbot can answer questions, but it often loses track of structured tasks.

Ivory is stronger because:

- it remembers the quote step
- it validates user input
- it keeps quote data on the backend
- it does not rely on the AI model to do quote math
- it can resume after interruptions

The short version:

It behaves like a chatbot when answering questions, but like a workflow engine when collecting a quote.

## How To Explain The Knowledge Base

You can say:

The chatbot answers insurance questions using a set of markdown files that act like its handbook.

Those files contain:

- product overviews
- coverage explanations
- deductibles and exclusions
- quote-readiness guidance
- claims examples
- FAQ-style answers

So when someone asks a question, the assistant is not supposed to invent an answer from nowhere. It is supposed to answer based on that stored reference material.

## How To Explain The Quote Logic

You can say:

The quote itself is not invented by the AI.

The AI helps with conversation, but the actual quote uses fixed business rules.

That means:

- the required fields are predefined
- each answer is validated
- the final quote is calculated in code

This makes the quote flow more reliable and easier to defend in a demo.

## How To Explain Why The Backend Matters

You can say:

The backend is the memory and decision-maker.

It stores:

- what mode the chat is in
- which insurance product the user picked
- what quote step they are on
- what information has already been collected
- whether a quote result already exists

So even if the chat feels conversational, the important workflow state is controlled by the backend, not guessed by the frontend.

## How To Explain The Frontend

You can say:

The frontend is mainly the presentation layer.

It:

- shows the streaming answer
- displays the current quote state
- shows the quote summary
- lets the user reset, adjust, or continue
- allows exporting quote details as JSON or CSV

The frontend does not decide the quote logic. It reflects what the backend sends back.

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

Ivory is a hybrid insurance assistant. It can answer product questions from a knowledge base, and it can also run a structured quote workflow for auto, home, and life insurance. The backend keeps the quote state, so if a user interrupts the flow with a question, the assistant answers it and then resumes from the exact next missing field. The quote itself is deterministic and calculated in code, not invented by the LLM.

## Slightly Longer Demo Answer

If you have around one minute, say this:

The easiest way to think about Ivory is as two systems in one chat. One part handles insurance questions using a markdown-based knowledge base. The other part handles quote collection like a guided checklist. The backend decides which path to use for each message. If the user starts a quote, the system collects the required fields step by step and validates each one. If the user interrupts with a policy question, the assistant answers it but keeps the quote state intact, then resumes the exact next step. Once all the data is collected, the final premium is calculated with deterministic rules in code. So the app feels conversational, but the transaction part remains stable and predictable.

## Best Phrases To Reuse

These are safe phrases to repeat in a demo:

- “It is a hybrid chat and workflow system.”
- “The backend is the source of truth.”
- “The quote flow is structured, not improvised.”
- “The LLM helps with language, not quote math.”
- “Users can interrupt the flow without losing progress.”
- “It answers like a chatbot, but behaves like a guided form when needed.”

## What To Avoid Saying

Avoid vague answers like:

- “It’s just an AI insurance bot.”
- “The model figures everything out.”
- “The frontend handles the flow.”
- “The quote is generated by AI.”

Those descriptions make the system sound weaker or less controlled than it really is.

## Good Q&A Prep

### If asked: “What is special about this app?”

Say:

The key part is not just that it answers questions. The key part is that it can pause and resume a structured quote flow without losing state.

### If asked: “Why not just use one prompt?”

Say:

Because open-ended chat and step-by-step transactions have different reliability needs. A single free-form prompt is much more likely to lose track of structured progress.

### If asked: “Why is the quote deterministic?”

Say:

Because quotes should be predictable, testable, and easier to validate. The AI handles conversation, but the premium logic lives in code.

### If asked: “What does the knowledge base do?”

Say:

It provides the factual grounding for insurance questions, so the assistant has a defined source of information instead of relying only on model memory.

### If asked: “What does the frontend do?”

Say:

It presents the conversation, current quote state, and results. It is the interface layer, not the workflow brain.

## Final Mental Shortcut

If you forget everything else, remember this:

Ivory is a chatbot with a checklist brain.

- handbook for questions
- checklist for quotes
- memory on the backend
- deterministic quote at the end
