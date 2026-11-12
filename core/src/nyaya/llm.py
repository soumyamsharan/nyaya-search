"""Language-model access: an OpenAI-compatible JSON client and a guard that enforces the daily cap and logs
metadata. Prompts and questions are never logged."""

import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, TypeVar

import httpx

from nyaya.errors import LlmBusyError, LlmUnavailableError
from nyaya.repos import LlmCallLog

log = logging.getLogger(__name__)
T = TypeVar("T")


@dataclass(frozen=True)
class LlmResult:
    content: dict
    tokens_in: int | None
    tokens_out: int | None


class JsonChatClient(Protocol):
    model: str

    def complete_json(self, system: str, user: str) -> LlmResult: ...


class OpenAICompatibleClient:
    """Works with Groq, Ollama and any other /chat/completions endpoint."""

    def __init__(self, base_url: str, model: str, api_key: str = "", timeout: float = 60.0,
                 transport: httpx.BaseTransport | None = None) -> None:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.model = model
        self._http = httpx.Client(base_url=base_url.rstrip("/"), headers=headers, timeout=timeout,
                                  transport=transport)

    def complete_json(self, system: str, user: str) -> LlmResult:
        payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        response = self._post_with_retry(payload)
        try:
            body = response.json()
            content = json.loads(body["choices"][0]["message"]["content"])
        except (ValueError, KeyError, IndexError) as exc:
            raise LlmUnavailableError("model returned malformed output") from exc
        usage = body.get("usage") or {}
        return LlmResult(content, usage.get("prompt_tokens"), usage.get("completion_tokens"))

    def _post_with_retry(self, payload: dict, attempts: int = 2) -> httpx.Response:
        for attempt in range(1, attempts + 1):
            try:
                response = self._http.post("/chat/completions", json=payload)
            except httpx.HTTPError as exc:
                if attempt == attempts:
                    raise LlmUnavailableError("model provider unreachable") from exc
                continue
            if response.status_code == 429:
                raise LlmBusyError("model provider rate limit reached")
            if response.status_code >= 500 and attempt < attempts:
                continue
            if response.is_error:
                raise LlmUnavailableError(f"model provider returned {response.status_code}")
            return response
        raise LlmUnavailableError("model provider unavailable")


class GuardedLlm:
    """Enforces the daily cap and records one metadata row per call."""

    def __init__(self, client: JsonChatClient, calls: LlmCallLog, daily_cap: int) -> None:
        self._client = client
        self._calls = calls
        self._daily_cap = daily_cap

    @property
    def model(self) -> str:
        return self._client.model

    def run(
        self,
        purpose: str,
        prompt_version: str,
        system: str,
        user: str,
        postprocess: Callable[[dict], tuple[T, int]],
    ) -> T:
        """Call the model, then postprocess(content) -> (value, sentences_dropped)."""
        meta = {"purpose": purpose, "model": self.model, "prompt_version": prompt_version}
        if self._calls.calls_today() >= self._daily_cap:
            self._calls.record(**meta, outcome="capped")
            raise LlmBusyError("daily limit for AI features reached")
        started = time.monotonic()
        try:
            result = self._client.complete_json(system, user)
            value, dropped = postprocess(result.content)
        except (LlmBusyError, LlmUnavailableError) as exc:
            self._calls.record(**meta, outcome=exc.code, latency_ms=int((time.monotonic() - started) * 1000))
            raise
        self._calls.record(
            **meta,
            outcome="ok",
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            latency_ms=int((time.monotonic() - started) * 1000),
            sentences_dropped=dropped,
        )
        return value
