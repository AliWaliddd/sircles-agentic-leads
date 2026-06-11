from __future__ import annotations

from sircles_agents.llm import MockLLMClient


def test_mock_llm_returns_fallback_without_api_key() -> None:
    client = MockLLMClient()

    response = client.complete(
        prompt_name="test_prompt",
        system_prompt="You are a helpful test model.",
        user_prompt="Return the fallback.",
        fallback="Expected deterministic response.",
    )

    assert response.text == "Expected deterministic response."
    assert response.provider == "mock"
    assert response.model == "mock-llm-v1"
    assert response.prompt_name == "test_prompt"
    assert response.metadata["deterministic"] is True


def test_mock_llm_preserves_metadata() -> None:
    client = MockLLMClient()

    response = client.complete(
        prompt_name="metadata_test",
        system_prompt="System",
        user_prompt="User",
        fallback="Fallback",
        metadata={"lead_id": "lead_saas_pursue"},
    )

    assert response.metadata["lead_id"] == "lead_saas_pursue"
    assert response.metadata["deterministic"] is True