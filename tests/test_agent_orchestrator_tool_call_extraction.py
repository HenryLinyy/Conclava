"""Regression tests for executor tool-call extraction."""

import pytest

from conclava.agent_orchestrator import _extract_tool_call


def test_extract_tool_call_accepts_openai_style_tool_call():
    assert _extract_tool_call(
        {"tool_call": {"name": "read_file", "input": {"path": "README.md"}}}
    ) == {"name": "read_file", "input": {"path": "README.md"}}


def test_extract_tool_call_accepts_qwable_tool_action_arguments_shape():
    """Qwable often emits {tool, action, arguments} instead of tool_call.

    The executor should normalize this instead of silently treating it as a
    final step_result. That lets validation decide whether the call is allowed
    and prevents malformed executor output from becoming a 500.
    """
    assert _extract_tool_call(
        {
            "tool": "terminal",
            "action": "run_command",
            "arguments": {
                "command": "python -m pytest",
                "description": "run tests",
            },
        }
    ) == {"name": "shell", "input": {"command": "python -m pytest"}}


def test_extract_tool_call_accepts_tool_call_input_json_string():
    """qwen3.6 fallback may emit input as a JSON string; normalize if valid."""
    assert _extract_tool_call(
        {"tool_call": {"name": "shell", "input": '{"command": "python -m pytest"}'}}
    ) == {"name": "shell", "input": {"command": "python -m pytest"}}


def test_extract_tool_call_rejects_tool_call_input_non_json_string():
    with pytest.raises(ValueError, match="tool_call input must be an object"):
        _extract_tool_call(
            {"tool_call": {"name": "shell", "input": "python -m pytest"}}
        )
