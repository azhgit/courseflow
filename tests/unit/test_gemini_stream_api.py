"""Unit tests for Gemini streaming API wiring."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from courseflow.infrastructure.llm.gemini import GeminiLLMClient


@pytest.mark.asyncio
async def test_stream_uses_generate_content_stream_api() -> None:
    """Streaming should call generate_content_stream (not stream=True kwarg)."""
    client = GeminiLLMClient(api_key="test-key")
    calls: list[dict[str, str]] = []

    def fake_generate_content_stream(*, model: str, contents: str):
        calls.append({"model": model, "contents": contents})
        return [SimpleNamespace(text="Hello "), SimpleNamespace(text="world")]

    client.client.models.generate_content_stream = fake_generate_content_stream  # type: ignore[attr-defined]

    output: list[str] = []
    async for chunk in client.stream(query="hi", context=["ctx"]):
        output.append(chunk)

    assert output == ["Hello ", "world"]
    assert len(calls) == 1
    assert calls[0]["model"] == client.model_name
