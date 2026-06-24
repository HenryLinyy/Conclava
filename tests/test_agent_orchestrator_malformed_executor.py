"""Regression tests: malformed executor/repair JSON must not 500.

Real-world bug: the executor model (e.g. qwen3-coder-next) emitted output that
contained braces but was not valid JSON ("Expecting ',' delimiter"). The final
brace-match fallback in ``_parse_json_object`` called ``json.loads`` without a
guard, so a ``json.JSONDecodeError`` escaped ``_execute_current_step`` (the
parse call sat OUTSIDE the try/except) and the whole request returned HTTP 500
with an empty body.

The fix normalizes the parse failure to ``ValueError`` and moves the executor
parse inside the existing graceful handler, so malformed output is retained as a
``final_answer`` step_result instead of crashing the request.
"""

import json

import pytest

from conclava.agent_orchestrator import _parse_json_object
from tests import test_agent_orchestrator as t


# Braces present (so the parser reaches the final brace-match fallback) but the
# JSON is invalid: missing comma between the two members.
_MALFORMED_WITH_BRACES = '{"a": "b" "c": "d"}'


def test_parse_json_object_raises_plain_valueerror_on_malformed_braces():
    """Must raise ValueError, NOT a leaking json.JSONDecodeError.

    json.JSONDecodeError subclasses ValueError, so asserting ValueError alone is
    not enough — we assert the leaked decoder error is normalized away.
    """
    with pytest.raises(ValueError) as exc_info:
        _parse_json_object(_MALFORMED_WITH_BRACES)
    assert not isinstance(exc_info.value, json.JSONDecodeError)


async def test_coding_workflow_malformed_executor_json_does_not_500(tmp_path):
    """Executor emits brace-y-but-invalid JSON → graceful final_answer, no raise."""
    planner_response = t._lmstudio_reasoning_response(
        content=t._planner_json(),
        reasoning_text="plan",
    )
    critic_response = t._lmstudio_reasoning_response(
        content=t._plan_critic_json(fatal=False),
        reasoning_text="ok",
    )
    # The executor returns content with braces but malformed JSON. Before the
    # fix this raised JSONDecodeError out of orchestrator.run() (-> HTTP 500).
    executor_response = t._lmstudio_reasoning_response(
        content='Here is the code: {"step_result": {"status": "done" "content": "x"}}',
        reasoning_text="emit code",
    )
    orchestrator, _client, _selector, _store, _compactor = t._orchestrator(
        tmp_path, [planner_response, critic_response, executor_response]
    )

    # Must not raise.
    action = await orchestrator.run(t._task("do a coding task"), "coding-workflow")

    assert action.type == "final_answer"
    # Raw executor output is retained rather than the request failing.
    assert "step_result" in (action.text or "") or "x" in (action.text or "")
