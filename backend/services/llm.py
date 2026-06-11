from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from env import load_project_env

load_project_env()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
DEFAULT_TIMEOUT_SECONDS = float(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "60"))
DEFAULT_MAX_RETRIES = int(os.getenv("OPENROUTER_MAX_RETRIES", "2"))
DEFAULT_HTTP_REFERER = os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost")
DEFAULT_TITLE = os.getenv("OPENROUTER_APP_TITLE", "Ivory Insurance Assistant")


class OpenRouterError(RuntimeError):
    """Raised when the OpenRouter request fails or returns an invalid payload."""


class OpenRouterConfigError(OpenRouterError):
    """Raised when the client is missing mandatory configuration."""


@dataclass(slots=True)
class OpenRouterResponse:
    content: str
    raw: dict[str, Any]
    model: str
    usage: dict[str, Any] | None = None


class OpenRouterClient:
    """Minimal OpenRouter chat client built on the standard library."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_referer: str = DEFAULT_HTTP_REFERER,
        app_title: str = DEFAULT_TITLE,
    ) -> None:
        self.api_key = (api_key or os.getenv("OPENROUTER_API_KEY", "")).strip()
        self.model = (model or DEFAULT_MODEL).strip()
        self.timeout_seconds = float(timeout_seconds)
        self.max_retries = max(0, int(max_retries))
        self.http_referer = http_referer
        self.app_title = app_title

        if not self.api_key:
            raise OpenRouterConfigError(
                "OPENROUTER_API_KEY is required to use OpenRouterClient."
            )

    @classmethod
    def from_env(cls) -> "OpenRouterClient":
        return cls()

    def _headers(self, extra_headers: Mapping[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.http_referer,
            "X-Title": self.app_title,
        }
        if extra_headers:
            headers.update({str(key): str(value) for key, value in extra_headers.items()})
        return headers

    def _request_json(
        self,
        payload: Mapping[str, Any],
        *,
        extra_headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        request = urllib.request.Request(
            OPENROUTER_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(extra_headers),
            method="POST",
        )

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    body = response.read().decode("utf-8")
                parsed = json.loads(body)
                if not isinstance(parsed, dict):
                    raise OpenRouterError("Unexpected OpenRouter response shape.")
                return parsed
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(min(0.5 * (2**attempt), 4.0))

        raise OpenRouterError(f"OpenRouter request failed: {last_error}") from last_error

    def chat(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 512,
        top_p: float = 1.0,
        response_format: Mapping[str, Any] | None = None,
        extra_headers: Mapping[str, str] | None = None,
    ) -> OpenRouterResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [dict(message) for message in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": False,
        }
        if response_format is not None:
            payload["response_format"] = dict(response_format)

        raw = self._request_json(payload, extra_headers=extra_headers)
        content = self._extract_content(raw)
        usage = raw.get("usage") if isinstance(raw.get("usage"), dict) else None
        return OpenRouterResponse(
            content=content,
            raw=raw,
            model=str(raw.get("model") or self.model),
            usage=usage,
        )

    def chat_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        history: Sequence[Mapping[str, Any]] | None = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        top_p: float = 1.0,
        response_format: Mapping[str, Any] | None = None,
        on_token: Callable[[str], None] | None = None,
    ) -> str:
        """Return the assistant reply as a plain string.

        *history* is an optional list of prior ``{role, content}`` turns placed
        between the system prompt and the current user prompt, so the model can
        resolve follow-up questions ("what is the max benefit?") in context.

        When *on_token* is provided the request uses OpenRouter's streaming
        API and each content delta is forwarded to the callback as it arrives.
        The complete assembled response is still returned for callers that need
        the full text (e.g. rag_answer stores it in state).
        """
        if on_token is not None:
            return self._stream_chat_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                history=history,
                temperature=temperature,
                max_tokens=max_tokens,
                on_token=on_token,
            )

        response = self.chat(
            self._compose_messages(system_prompt, history, user_prompt),
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            response_format=response_format,
        )
        return response.content

    @staticmethod
    def _compose_messages(
        system_prompt: str,
        history: Sequence[Mapping[str, Any]] | None,
        user_prompt: str,
    ) -> list[dict[str, str]]:
        """Build the messages array: system + sanitized history + current user."""
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for turn in history or []:
            role = str(turn.get("role", ""))
            content = turn.get("content")
            if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_prompt})
        return messages

    def _stream_chat_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        history: Sequence[Mapping[str, Any]] | None = None,
        temperature: float,
        max_tokens: int,
        on_token: Callable[[str], None],
    ) -> str:
        """Stream tokens via *on_token* callback; return the full assembled content."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._compose_messages(system_prompt, history, user_prompt),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        request = urllib.request.Request(
            OPENROUTER_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        full_content = ""
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    for raw_line in response:
                        line = raw_line.decode("utf-8").rstrip("\r\n")
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = (
                                chunk.get("choices", [{}])[0]
                                .get("delta", {})
                                .get("content") or ""
                            )
                            if delta:
                                on_token(delta)
                                full_content += delta
                        except (json.JSONDecodeError, IndexError, KeyError):
                            continue
                return full_content
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(min(0.5 * (2**attempt), 4.0))

        raise OpenRouterError(
            f"Streaming request failed after {self.max_retries + 1} attempts: {last_error}"
        ) from last_error

    def chat_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> dict[str, Any]:
        content = self.chat_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise OpenRouterError(
                f"OpenRouter returned non-JSON content: {content[:120]!r}"
            ) from exc
        if not isinstance(parsed, dict):
            raise OpenRouterError("OpenRouter JSON response was not an object.")
        return parsed

    @staticmethod
    def _extract_content(payload: Mapping[str, Any]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise OpenRouterError("OpenRouter response is missing choices.")

        choice = choices[0]
        if not isinstance(choice, Mapping):
            raise OpenRouterError("OpenRouter response choice has invalid shape.")

        message = choice.get("message")
        if isinstance(message, Mapping):
            content = message.get("content")
            if isinstance(content, str):
                return content.strip()

        text = choice.get("text")
        if isinstance(text, str):
            return text.strip()

        raise OpenRouterError("OpenRouter response did not include assistant content.")


def build_default_client() -> OpenRouterClient:
    return OpenRouterClient.from_env()
