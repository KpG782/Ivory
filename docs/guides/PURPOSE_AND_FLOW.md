# Ivory Purpose And Flow

## What this project is

Ivory is a hybrid insurance assistant.

It is not just a chatbot and it is not just a quote form.

Its purpose is to combine:

- conversational insurance Q&A
- structured quote collection
- clean switching between those two modes

That is the main point of the project from [MASTER.md](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/docs/specs/MASTER.md): prove that one assistant can answer product questions and also run a guided transactional workflow without losing state.

## Why this exists

The use case is simple:

- a user wants to learn about insurance products
- the same user may decide to ask for a quote
- while getting that quote, the user may interrupt with product questions
- the assistant should answer the question and then continue the quote flow

So the product value is:

- fewer drop-offs than a rigid quote form
- better user guidance than a static FAQ page
- one continuous experience instead of separate support and quoting tools

## When someone would use this

Typical cases:

- `What types of insurance do you offer?`
- `What does comprehensive auto coverage include?`
- `I want a quote for auto insurance.`
- `I started a quote, but I need to ask something before I continue.`

The whole project is meant for a user who is still deciding, still learning, or partially ready to buy.

## Core product idea

This project has two modes.

### 1. Conversational mode

The assistant answers insurance questions using the knowledge base.

Examples:

- coverage details
- exclusions
- claims process
- pricing tier differences
- eligibility FAQs

### 2. Transactional mode

The assistant guides the user through quote collection.

Examples:

- identify insurance type
- collect required details
- validate inputs
- generate a quote
- let the user confirm, adjust, or restart

## Why the state machine matters

This project uses a state-machine style backend because normal chat is not enough for quoting.

A quote flow needs memory of:

- what product the user chose
- what fields are already collected
- what field is missing next
- whether the user is confirming or adjusting

Without state, the assistant would lose context too easily and the quote flow would feel unreliable.

## Frontend flow

The frontend is intentionally simple now.

### Main dashboard: `/`

This is the main working page.

The user can:

- ask product questions
- start a quote
- continue answering quote questions
- reset the session
- see the current backend state
- see the current quote summary

The dashboard is the primary workspace.

### What the user sees on the dashboard

There are three practical parts:

1. The main chat area
   This is where the conversation happens.

2. The session state panel
   This shows:
   - current mode
   - insurance type
   - current step
   - next required field

3. The quote summary card
   This shows the generated quote when available.

### Confirmation page: `/quote-confirmation`

This page is only for the final confirmation stage.

It should only be used when the backend says the session is ready for confirmation.

That means:

- `mode = transactional`
- `quote_step = confirm`
- a real `quote_result` exists

On this page, the user can:

- accept the quote
- adjust coverage

## Backend flow

The backend is the source of truth.

It decides:

- whether the user is in conversational or transactional mode
- what the current quote step is
- what field is missing
- whether a quote is ready
- whether the session is in confirmation state

The frontend should not invent this state on its own.

### Current backend endpoints

- `GET /health`
- `POST /chat`
- `POST /reset`

### Current backend session behavior

Each chat session tracks structured state, including:

- `mode`
- `intent`
- `quote_step`
- `insurance_type`
- `current_field`
- `quote_result`

That is what keeps the chat and quote flow consistent across the UI.

## Typical user journey

### Journey A: question only

1. User opens the dashboard.
2. User asks an insurance question.
3. Backend routes to the knowledge path.
4. Assistant answers using retrieved knowledge base content.

### Journey B: quote flow

1. User says they want a quote.
2. Backend switches into transactional mode.
3. Assistant asks for required fields.
4. User answers step by step.
5. Backend validates the data.
6. Backend generates a quote.
7. User reviews and accepts or adjusts.

### Journey C: mid-flow interruption

1. User starts a quote.
2. Assistant is collecting quote details.
3. User interrupts with a product question.
4. Backend answers the question.
5. Backend preserves collected quote data.
6. Assistant resumes the quote flow.

That third journey is one of the most important reasons this project is worth using.

## Why use this instead of a normal form

A normal quote form is faster to build, but worse at handling uncertainty.

This assistant is useful because it can:

- educate while collecting quote data
- reduce friction when the user is unsure
- recover cleanly from interruptions
- keep one conversation instead of forcing the user through separate pages and tools

So the value is not just “chat UI”.

The value is:

- guided decision support
- structured quote handling
- context preservation

## About adding more knowledge base content

Yes, adding more knowledge base content can help, but only if it is targeted.

### When more knowledge base content helps

It helps when you add information that improves real product questions, such as:

- product coverage details
- exclusions and limitations
- deductible rules
- claim filing steps
- policy renewal and cancellation rules
- bundling discounts
- eligibility rules
- product comparisons

This makes conversational mode more useful and makes the demo feel more complete.

### When more knowledge base content does not help much

It does not help much if you add a lot of repetitive or low-signal text.

Examples:

- multiple chunks saying the same thing
- marketing copy without factual value
- content unrelated to the actual user prompts
- large policy text that the assistant never needs

Too much noisy content can weaken retrieval quality.

## Best knowledge base strategy for this project

The best approach is:

- keep the knowledge base compact
- cover the most likely user questions well
- organize content by product and policy topic
- avoid duplicate chunks
- prefer short, clear, factual documents over long vague ones

Good categories to expand next:

- auto coverage inclusions and exclusions
- home coverage scenarios
- life policy eligibility and exclusions
- claims examples
- deductible and coverage-level comparisons
- cancellation and refund policy

## Short version

This project is useful because it combines:

- insurance Q&A
- guided quote generation
- stateful interruption handling

The frontend gives the user one main dashboard to work through that flow.
The backend keeps the flow consistent.
The knowledge base supports grounded answers.

If you expand the knowledge base, do it to improve answer quality for likely insurance questions, not just to make the repo look bigger.
