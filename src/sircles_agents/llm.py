from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class LLMResponse:
    """
    Structured response from an LLM-like client.

    The mock implementation returns deterministic fallback text so the project
    remains runnable without API keys.
    """

    text: str
    provider: str
    model: str
    prompt_name: str
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMClient(Protocol):
    """
    Interface for LLM providers.

    A real OpenAI/Anthropic/Gemini/local-model client could implement this
    interface later while keeping the agent contracts unchanged.
    """

    def complete(
        self,
        *,
        prompt_name: str,
        system_prompt: str,
        user_prompt: str,
        fallback: str,
        metadata: dict[str, Any] | None = None,
    ) -> LLMResponse:
        ...


class MockLLMClient:
    """
    Deterministic mock LLM client.

    This deliberately does not call an external API. It simulates the LLM layer
    while keeping tests reproducible and API keys out of the repo.
    """

    def __init__(self, model: str = "mock-llm-v1") -> None:
        self.model = model

    def complete(
        self,
        *,
        prompt_name: str,
        system_prompt: str,
        user_prompt: str,
        fallback: str,
        metadata: dict[str, Any] | None = None,
    ) -> LLMResponse:
        response_metadata = dict(metadata or {})
        response_metadata.update(
            {
                "deterministic": True,
                "system_prompt_chars": len(system_prompt),
                "user_prompt_chars": len(user_prompt),
            }
        )

        return LLMResponse(
            text=fallback,
            provider="mock",
            model=self.model,
            prompt_name=prompt_name,
            metadata=response_metadata,
        )