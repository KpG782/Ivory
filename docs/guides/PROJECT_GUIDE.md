# Ivory Project Guide

## Purpose

This guide explains what the Ivory chatbot project is, how it works now, and which technology choices shape the current implementation.

It is meant to help a junior engineer quickly understand the project without reading every root-level markdown file first.

## Current Repository Status

The repository now contains the working application source code as well as the supporting design and audit docs.

Present now:
- `backend/` FastAPI + LangGraph backend
- `frontend/` Next.js frontend
- `tests/` backend integration tests
- `docs/` specs, guides, audits, and reports
- `docker-compose.backend.yml` and backend container files
- `env.example`

## Product Goal

The intended product is an AI insurance assistant for Ivory.

It has two responsibilities:
- answer questions about insurance products
- guide users through a quote-generation workflow

Example user behaviors:
- "What does comprehensive coverage include?"
- "I want a quote for auto insurance."

The system is designed to handle both kinds of requests in one conversation.

## Core Architecture

The current architecture is a **LangGraph state machine** with two main modes:

- `conversational`
  Handles product questions using RAG.

- `transactional`
  Handles the structured insurance quote flow.

### Why a state machine is used

Insurance quoting is not just open-ended chat. It is a step-by-step workflow with required fields, validation, and confirmation.

A state machine is useful because it:
- tracks the current step
- preserves structured data
- routes the user to the correct next action
- allows interruptions without losing progress

## Key Design Feature

The most important engineering behavior in this project is **graceful mid-flow switching**.

Example:
1. User starts an auto insurance quote.
2. The bot collects vehicle details.
3. The user asks a product question in the middle of the flow.
4. The bot answers the question.
5. The bot resumes the quote flow from the same step with previously collected data still intact.

This is the main feature that differentiates the design from a simple chatbot prompt wrapper.

## Intent Model

The system is designed to classify each user message into one of three intents:

- `question`
  Product or policy question, routed to RAG.

- `quote`
  New or continued request to get an insurance quote.

- `response`
  Answer to a bot prompt during the quote flow.

The `response` intent is especially important. Without it, the system might mistake a field value like `"2019 Toyota Camry"` for a new conversation request instead of quote data.

## Graph Nodes

The current backend uses these nodes:

- `router`
  Classifies intent and routes to the correct branch.

- `rag_answer`
  Retrieves relevant knowledge base content and generates a grounded answer.

- `identify_product`
  Determines the insurance product type: auto, home, or life.

- `collect_details`
  Asks for the required fields for the selected product.

- `validate_quote`
  Validates user input and calculates the quote.

- `confirm`
  Lets the user accept, adjust, or restart.

## State Shape

The conversation state includes fields such as:

- `messages`
- `mode`
- `intent`
- `quote_step`
- `insurance_type`
- `collected_data`
- `quote_result`
- `pending_question`

This state lets the application behave like a workflow engine rather than a stateless chatbot.

## Retrieval and LLM Layer

The RAG design is:

- documents are stored in a knowledge base
- embeddings are generated with `sentence-transformers`
- vectors are stored in `ChromaDB`
- retrieved context is passed to an LLM through `OpenRouter`

### Why this matters

This keeps product answers grounded in source material instead of relying only on the model's general memory.

Benefits:
- better factual consistency
- easier content updates
- lower hallucination risk

## Current Tech Stack

- Backend: Python, FastAPI, LangGraph
- LLM access: OpenRouter
- Embeddings: `sentence-transformers`
- Vector store: ChromaDB
- Frontend: Next.js, React, TypeScript, Tailwind CSS
- Streaming: SSE
- Local orchestration: backend-focused Docker Compose

## Quote Flow Design

The intended quote flow is:

1. detect quote intent
2. identify insurance product
3. collect required fields
4. validate inputs
5. calculate premium
6. confirm, adjust, or restart

### Planned quote inputs by product

Auto insurance:
- vehicle year
- vehicle make
- vehicle model
- driver age
- accident history
- coverage level

Home insurance:
- property type
- location
- estimated property value
- year built
- coverage level

Life insurance:
- age
- health status
- smoker flag
- coverage amount
- term years
- coverage level

## Quote Calculation

The project docs intentionally describe a simple premium calculator using:

`base_rate × risk_multipliers`

This is a practical design choice for an assessment because it keeps business logic deterministic while allowing the LLM to focus on routing and language generation.

## API and Frontend Design

The intended backend API includes:
- `POST /chat`
- `GET /health`
- `POST /reset`

The chat endpoint is supposed to stream responses using **Server-Sent Events (SSE)** so the frontend can render tokens progressively.

The intended frontend is a React chat UI with components such as:
- chat window
- message bubble
- typing indicator
- quote card

## Environment Variables

The repository includes `env.example` with these intended variables:

- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`
- `CHROMA_PERSIST_DIR`

### Important note

`env.example` is a sample configuration file, not a Python virtual environment.

Difference:
- `venv` = Python package environment
- `.env` or `env.example` = runtime configuration values

## Security Note

`env.example` is currently sanitized and uses placeholders only, which is the correct setup.

Recommended practice:
1. keep real secrets only in a local `.env` file
2. never commit live API keys into `env.example`
3. rotate any key immediately if it is ever exposed

## Strengths Of The Design

- clear separation between conversational and transactional behavior
- good use of explicit state management
- practical RAG architecture for domain-specific Q&A
- business logic kept outside the LLM
- streaming response design improves perceived speed

## Current Gaps

The main remaining gaps are no longer core implementation gaps. They are mostly follow-up hardening items:

- durable shared session persistence for multi-instance deployment
- broader browser/E2E automation
- deeper evaluation coverage for intent and RAG quality
- stronger production-oriented rate limiting and abuse controls

## Recommended Next Steps

If this repository is going to move from design to implementation, the most sensible order is:

1. scaffold the backend structure
2. define `ChatState`
3. implement router and transactional nodes
4. implement vector store ingestion and RAG node
5. expose FastAPI endpoints with SSE
6. build the React chat frontend
7. add end-to-end flow tests

## Short Explanation For A Junior Engineer

If you need to explain this quickly:

> This project is a planned full-stack AI insurance assistant. It combines RAG-based product Q&A with a structured quote workflow powered by a LangGraph state machine. The main engineering goal is to preserve user progress during quote generation even if the user interrupts the flow with product questions.

## Short Explanation For A Non-Technical Person

> It is a chatbot for an insurance company that can answer questions and help customers get quotes without losing progress if the conversation changes direction.
