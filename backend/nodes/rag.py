from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping, Sequence

from services.llm import OpenRouterClient, OpenRouterError
from services.vectorstore import RetrievedChunk, search_knowledge_base
from streaming_context import get_on_token

logger = logging.getLogger("shieldbase.rag")

RAG_SYSTEM_PROMPT = """You are the ShieldBase insurance assistant.
Answer only using the provided knowledge base context.
If the context is insufficient, say so plainly and do not invent policy details.
Keep the answer concise, accurate, and friendly.
If the user is in the middle of a quote flow, answer the question and do not reset quote progress.
"""


@dataclass(slots=True)
class RagAnswer:
    content: str
    sources: list[dict[str, Any]]
    query: str
    fallback_used: bool = False


def rag_answer(
    state: Mapping[str, Any],
    *,
    top_k: int = 4,
    client: OpenRouterClient | None = None,
    kb_dir: str | None = None,
    persist_dir: str | None = None,
) -> dict[str, Any]:
    """Answer a product question while preserving any transactional state."""

    state_copy: dict[str, Any] = dict(state)
    messages = _normalize_messages(state_copy.get("messages"))
    query = _extract_query(state_copy, messages)

    if not query:
        logger.warning("rag_answer: no query extracted from state")
        return _append_message(
            state_copy,
            messages,
            "I could not identify a question to answer. Please ask about a policy, coverage, or quote topic.",
            [],
            fallback_used=True,
            error="Missing question text for RAG response.",
        )

    logger.debug("rag_answer: query=%r top_k=%d", query, top_k)

    try:
        retrieved = search_knowledge_base(
            query,
            top_k=top_k,
            kb_dir=kb_dir,
            persist_dir=persist_dir,
        )
        logger.debug(
            "rag_answer: retrieved %d chunks — %s",
            len(retrieved),
            [f"{r.source}(score={r.score:.3f})" for r in retrieved],
        )
    except Exception as exc:
        retrieved = []
        retrieval_error = str(exc)
        logger.error("rag_answer: retrieval exception — %s", exc)
    else:
        retrieval_error = None

    if not retrieved:
        logger.error(
            "rag_answer: empty retrieval for query=%r error=%r — "
            "run the ingestion script: python -c \"from services.vectorstore import ingest_knowledge_base; ingest_knowledge_base()\"",
            query,
            retrieval_error,
        )
        return _append_message(
            state_copy,
            messages,
            "I do not have enough knowledge-base context to answer that confidently right now.",
            [],
            fallback_used=True,
            error=retrieval_error or "No retrieval results returned.",
        )

    rag_client = client or _build_client_or_none()
    if rag_client is None:
        logger.warning("rag_answer: no LLM client available (missing OPENROUTER_API_KEY?) — using formatted fallback")
        fallback_answer = _format_fallback_answer(query, retrieved)
        return _append_message(
            state_copy,
            messages,
            fallback_answer,
            retrieved,
            fallback_used=True,
            error=retrieval_error,
        )

    # Use the streaming callback from the request thread if available.
    # get_on_token() returns None when called outside a streaming context
    # (e.g. in unit tests), which causes chat_text to use the non-streaming path.
    on_token = get_on_token() if client is None else None

    prompt = _build_prompt(query, retrieved)
    history = _recent_history(messages, query)
    logger.debug(
        "rag_answer: calling LLM model=%s streaming=%s history_turns=%d",
        rag_client.model,
        on_token is not None,
        len(history),
    )
    try:
        content = rag_client.chat_text(
            system_prompt=RAG_SYSTEM_PROMPT,
            user_prompt=prompt,
            history=history,
            temperature=0.2,
            max_tokens=450,
            on_token=on_token,
        )
        logger.debug("rag_answer: LLM responded OK, len=%d", len(content))
    except (OpenRouterError, Exception) as exc:
        logger.error("rag_answer: LLM call failed — %s", exc)
        content = _format_fallback_answer(query, retrieved)
        return _append_message(
            state_copy,
            messages,
            content,
            retrieved,
            fallback_used=True,
            error=str(exc),
        )

    return _append_message(
        state_copy,
        messages,
        content,
        retrieved,
        fallback_used=False,
        error=retrieval_error,
    )


def answer_rag_question(state: Mapping[str, Any], **kwargs: Any) -> dict[str, Any]:
    return rag_answer(state, **kwargs)


def _build_client_or_none() -> OpenRouterClient | None:
    try:
        return OpenRouterClient.from_env()
    except Exception:
        return None


def _extract_query(state: Mapping[str, Any], messages: Sequence[dict[str, Any]]) -> str:
    pending_question = state.get("pending_question")
    if isinstance(pending_question, str) and pending_question.strip():
        return pending_question.strip()

    for message in reversed(messages):
        role = str(message.get("role", "")).lower()
        content = message.get("content")
        if role in {"user", "human"} and isinstance(content, str) and content.strip():
            return content.strip()

    raw_message = state.get("message")
    if isinstance(raw_message, str) and raw_message.strip():
        return raw_message.strip()

    return ""


def _recent_history(
    messages: Sequence[dict[str, Any]],
    current_query: str,
    *,
    max_turns: int = 6,
) -> list[dict[str, str]]:
    """Return the recent prior turns (excluding the current question) for the LLM.

    The last message is the question being answered now (already embedded in the
    prompt), so it is dropped. We keep the most recent ``max_turns`` user/
    assistant exchanges so follow-ups resolve in context without sending the
    entire transcript.
    """
    prior = list(messages[:-1]) if messages else []
    turns: list[dict[str, str]] = []
    for message in prior:
        role = str(message.get("role", ""))
        content = message.get("content")
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            turns.append({"role": role, "content": content})
    return turns[-(max_turns * 2):]


def _normalize_messages(messages: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    if not isinstance(messages, list):
        return normalized

    for message in messages:
        if isinstance(message, dict):
            normalized.append(
                {
                    "role": str(message.get("role", "user")),
                    "content": message.get("content", ""),
                }
            )
        elif isinstance(message, str):
            normalized.append({"role": "user", "content": message})
    return normalized


def _build_prompt(query: str, retrieved: Sequence[RetrievedChunk]) -> str:
    context_lines = []
    for index, chunk in enumerate(retrieved, start=1):
        source = chunk.source or chunk.title or f"source-{index}"
        context_lines.append(f"[{index}] {source}\n{chunk.content.strip()}")

    context_block = "\n\n".join(context_lines)
    return f"""Question:
{query}

Knowledge base context:
{context_block}

Instructions:
- Answer only from the context.
- Mention the source if helpful.
- If the context does not fully answer the question, say what is missing.
"""


def _format_fallback_answer(query: str, retrieved: Sequence[RetrievedChunk]) -> str:
    query_lower = query.strip().lower()
    direct_answer = _direct_fallback_answer(query_lower, retrieved)
    if direct_answer:
        return direct_answer

    summary = _summarize_chunk(retrieved[0]) if retrieved else ""
    if summary:
        return summary

    return "I do not have enough information in the knowledge base to answer that confidently."


def _direct_fallback_answer(query: str, retrieved: Sequence[RetrievedChunk]) -> str | None:
    combined = " ".join(chunk.content.lower() for chunk in retrieved[:3])

    if "comprehensive" in query:
        if any(term in combined for term in ("theft", "vandalism", "weather", "fire", "non-collision")):
            return (
                "Comprehensive coverage generally includes non-collision damage such as "
                "theft, vandalism, fire, and weather-related damage."
            )

    if "what insurance products" in query or "types of insurance" in query or "what do you offer" in query:
        if all(term in combined for term in ("auto", "home", "life")):
            return "ShieldBase offers auto insurance, home insurance, and life insurance."

    if "deductible" in query:
        return (
            "A deductible is the amount the policyholder pays before covered property or vehicle "
            "damage benefits apply."
        )

    if "flood" in query and "home" in query:
        return "Standard home insurance usually does not cover flood damage unless separate flood coverage exists."

    if "beneficiar" in query:
        return "A beneficiary is the person or entity selected to receive the life insurance death benefit."

    return None


def _summarize_chunk(chunk: RetrievedChunk) -> str:
    text = chunk.content.strip()
    if not text:
        return ""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    bullet_lines = [line.lstrip("- ").strip() for line in lines if line.startswith("-")]
    if bullet_lines:
        return bullet_lines[0].rstrip(".") + "."

    prose_lines = [line for line in lines if not line.startswith("#")]
    if not prose_lines:
        return ""

    sentence = prose_lines[0]
    if len(sentence) > 220:
        sentence = sentence[:220].rsplit(" ", 1)[0]
    return sentence.rstrip(".") + "."


def _append_message(
    state: MutableMapping[str, Any],
    messages: list[dict[str, Any]],
    content: str,
    retrieved: Sequence[RetrievedChunk],
    *,
    fallback_used: bool,
    error: str | None,
) -> dict[str, Any]:
    updated_messages = list(messages)
    updated_messages.append({"role": "assistant", "content": content})

    state["messages"] = updated_messages
    state["pending_question"] = None
    state["last_error"] = error if error else ("RAG fallback used." if fallback_used else None)
    state["mode"] = state.get("mode", "conversational")
    return dict(state)
