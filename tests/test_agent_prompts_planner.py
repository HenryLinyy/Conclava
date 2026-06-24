"""Regression tests for planner prompt shaping with local reasoning models."""

from conclava.agent_prompts import build_planner_messages
from conclava.context_pack import ContextPack
from conclava.schemas import ParsedAgentTask


def _task(text: str = "寫一個 Python function 計算 Fibonacci 第 n 項") -> ParsedAgentTask:
    return ParsedAgentTask(
        text=text,
        tools=[],
        tool_results=[],
        profile="conclava-code-agent",
        source_protocol="openai_responses",
        stream=False,
        raw_request={},
    )


def test_planner_messages_disable_qwen_thinking_at_system_and_user_boundaries():
    """Qwen3.6 planner burns the whole max_tokens budget in reasoning mode.

    LM Studio reports completion_tokens_details.reasoning_tokens ~= max_tokens,
    leaving `content` as partial JSON and causing planner_json_parse_failed.
    Empirically, the local qwen/qwen3.6-35b-a3b planner only reliably emits
    parseable JSON for trivial prompts when `/no_think` is present in BOTH the
    system message and the user message.
    """
    messages = build_planner_messages(
        _task(),
        ContextPack(goal="test", workflow="coding-workflow"),
    )

    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[0]["content"].lstrip().startswith("/no_think")
    assert messages[1]["content"].lstrip().startswith("/no_think")
    assert "只輸出 JSON" in messages[0]["content"]
    assert "不要輸出任何思考過程" in messages[0]["content"]
    assert "standalone function" in messages[0]["content"]
    assert "不要建立檔案" in messages[0]["content"]
    assert "不要要求 shell 執行" in messages[0]["content"]
