"""Regression tests for executor / repair prompts with local reasoning models."""

from conclava.agent_prompts import build_executor_messages, build_repair_messages
from conclava.agent_state import AgentRun, AgentStep, new_id
from conclava.context_pack import ContextPack


def _run() -> AgentRun:
    run = AgentRun.create(goal="test", workflow="coding-workflow")
    run.plan = [
        AgentStep(
            step_id=new_id("step"),
            title="write code",
            intent="write a small function",
            required_tools=["edit_file"],
            success_criteria=["code exists"],
            failure_criteria=["missing code"],
        )
    ]
    run.current_step_index = 0
    return run


def _context() -> ContextPack:
    return ContextPack(goal="test", workflow="coding-workflow")


def test_executor_messages_disable_qwen_thinking_at_system_and_user_boundaries():
    run = _run()
    messages = build_executor_messages(run, _context(), run.current_step())

    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[0]["content"].lstrip().startswith("/no_think")
    assert messages[1]["content"].lstrip().startswith("/no_think")
    assert "只輸出 JSON" in messages[0]["content"]
    assert "不要輸出任何思考過程" in messages[0]["content"]
    assert "STRICT OUTPUT CONTRACT" in messages[0]["content"]
    assert "step_result" in messages[0]["content"]
    assert "Do NOT output top-level" in messages[0]["content"]
    assert "Do not request shell for non-test commands" in messages[0]["content"]
    assert "standalone function or code snippet" in messages[0]["content"]
    assert "do not inspect files" in messages[0]["content"]
    assert "unavailable aliases" in messages[0]["content"]


def test_repair_messages_disable_qwen_thinking_at_system_and_user_boundaries():
    run = _run()
    messages = build_repair_messages(run, _context(), "pytest failed")

    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[0]["content"].lstrip().startswith("/no_think")
    assert messages[1]["content"].lstrip().startswith("/no_think")
    assert "只輸出 JSON" in messages[0]["content"]
    assert "不要輸出任何思考過程" in messages[0]["content"]
