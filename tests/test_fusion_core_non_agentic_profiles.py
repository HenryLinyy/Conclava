"""Regression tests: hermes-pro / agentic-mlx / formatter-mlx prompts must
include `/no_think` on both system and user boundaries (qwen3.6 thinking
would otherwise consume the entire token budget)."""

import pytest

from conclava.fusion_core import FusionCore
from conclava.config import FusionConfig
from conclava.schemas import ParsedAgentTask


def _task(profile: str) -> ParsedAgentTask:
    return ParsedAgentTask(
        text="用繁體中文 10 字內回答：OK",
        tools=[],
        tool_results=[],
        profile=profile,
        source_protocol="openai_responses",
        stream=False,
        raw_request={"input": "用繁體中文 10 字內回答：OK"},
    )


def test_hermes_pro_prompt_disables_qwen_thinking(monkeypatch):
    captured: list[dict] = []

    class _FakeClient:
        def chat_completion(self, *, model, messages, max_tokens, stream=False, temperature=0.7, tools=None):
            captured.append({"model": model, "messages": messages, "max_tokens": max_tokens, "tools": tools})
            return {
                "choices": [
                    {"message": {"content": "OK"}, "finish_reason": "stop"}
                ]
            }

    core = FusionCore(FusionConfig(agent_store_path="/tmp/_nothink_test.sqlite3"))
    core.ollama = _FakeClient()
    import asyncio
    asyncio.run(core._run_hermes_pro_agent(_task("hermes-pro")))
    msgs = captured[0]["messages"]
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"].lstrip().startswith("/no_think")
    assert any(m["role"] == "user" and m["content"].lstrip().startswith("/no_think") for m in msgs)


def test_agentic_mlx_prompt_disables_qwen_thinking(monkeypatch):
    captured: list[dict] = []

    class _FakeClient:
        def chat_completion(self, *, model, messages, max_tokens, stream=False, temperature=0.7, tools=None):
            captured.append({"model": model, "messages": messages, "max_tokens": max_tokens, "tools": tools})
            return {
                "choices": [
                    {"message": {"content": "OK"}, "finish_reason": "stop"}
                ]
            }

    core = FusionCore(FusionConfig(agent_store_path="/tmp/_nothink_test.sqlite3"))
    core.ollama = _FakeClient()
    import asyncio
    asyncio.run(core._run_agentic_mlx_agent(_task("agentic-mlx")))
    msgs = captured[0]["messages"]
    assert msgs[0]["content"].lstrip().startswith("/no_think")
    assert any(m["role"] == "user" and m["content"].lstrip().startswith("/no_think") for m in msgs)


def test_formatter_mlx_prompt_disables_qwen_thinking(monkeypatch):
    captured: list[dict] = []

    class _FakeClient:
        def chat_completion(self, *, model, messages, max_tokens, stream=False, temperature=0.7, tools=None):
            captured.append({"model": model, "messages": messages, "max_tokens": max_tokens, "tools": tools})
            return {
                "choices": [
                    {"message": {"content": "OK"}, "finish_reason": "stop"}
                ]
            }

    core = FusionCore(FusionConfig(agent_store_path="/tmp/_nothink_test.sqlite3"))
    core.ollama = _FakeClient()
    import asyncio
    asyncio.run(core._run_formatter_mlx_agent(_task("formatter-mlx")))
    msgs = captured[0]["messages"]
    assert msgs[0]["content"].lstrip().startswith("/no_think")
    assert any(m["role"] == "user" and m["content"].lstrip().startswith("/no_think") for m in msgs)
