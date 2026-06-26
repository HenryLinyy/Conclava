"""Acceptance split tests for agent orchestrator planning flow."""

import json

from tests import test_agent_orchestrator as orchestrator_tests


def test_extract_agent_run_id_accepts_valid_metadata_only():
    orchestrator_tests.test_extract_agent_run_id_accepts_valid_metadata_only()


async def test_run_uses_model_selector_for_planner_and_executor(tmp_path):
    await orchestrator_tests.test_run_uses_model_selector_for_planner_and_executor(
        tmp_path
    )


async def test_invalid_planner_json_returns_failed_final_answer(tmp_path):
    await orchestrator_tests.test_invalid_planner_json_returns_failed_final_answer(
        tmp_path
    )


async def test_agentic_workflow_runs_plan_critic_before_executor(tmp_path):
    await orchestrator_tests.test_agentic_workflow_runs_plan_critic_before_executor(
        tmp_path
    )


async def test_agentic_workflow_blocks_on_fatal_plan_critic(tmp_path):
    await orchestrator_tests.test_agentic_workflow_blocks_on_fatal_plan_critic(tmp_path)


async def test_planner_prose_with_fenced_json_block_recovers(tmp_path):
    """Real-world bug: qwen3.6-35b-a3b emits 10K+ chars of 'Here's a thinking
    process: ...' prose with a ```json``` fence containing the real plan at
    the end. The current _parse_json_object only strips the FIRST and LAST
    ``` line, leaving the prose + the real block, which json.loads rejects.

    The fix: prefer extracting the LAST valid ```json``` fence from the raw
    output before falling back to the outer brace match.
    """
    from tests import test_agent_orchestrator as t

    plan = json.loads(t._planner_json())
    # Realistic model output: long thinking prose + schema illustration + real plan
    raw = (
        "Here's a thinking process:\n\n"
        "1.  **Analyze User Goal:**\n"
        "   - Compute Fibonacci with memoization.\n\n"
        "2.  **Schema reminder:**\n"
        "```json\n"
        + json.dumps({"steps": [{"title": "schema", "intent": "illustration"}]})
        + "\n```\n\n"
        "3.  **Real plan:**\n"
        "```json\n" + json.dumps(plan, ensure_ascii=False) + "\n```\n\n"
        "All constraints met. Proceeding."
    )
    planner_response = t._lmstudio_reasoning_response(
        content="",
        reasoning_text=raw,
    )
    critic_response = t._lmstudio_reasoning_response(
        content=t._plan_critic_json(fatal=False),
        reasoning_text="plan looks fine",
    )
    executor_response = t._lmstudio_reasoning_response(
        content=json.dumps(
            {"tool_call": {"name": "read_file", "input": {"path": "x.py"}}}
        ),
        reasoning_text="read x.py",
    )
    orchestrator, client, _selector, _store, _compactor = t._orchestrator(
        tmp_path, [planner_response, critic_response, executor_response]
    )

    action = await orchestrator.run(t._task("Plan fib"), "coding-workflow")

    # Planner must NOT have failed — the workflow should advance past it.
    assert action.type != "final_answer" or "planner_json_parse_failed" not in (
        action.text or ""
    ), f"planner failed unexpectedly: trace={action.trace!r}"
    # And the plan should have been parsed (≥1 step from the real block).
    assert (action.trace or {}).get("agent_status") != "failed", (
        f"workflow marked failed: {action.trace!r}"
    )


async def test_planner_plain_json_inside_prose_recovers(tmp_path):
    """Real-world bug variant: the planner emits prose wrapping a plain
    (non-fenced) JSON object. The parser should locate the JSON object via
    brace matching even when surrounded by reasoning text.
    """
    from tests import test_agent_orchestrator as t

    plan = json.loads(t._planner_json())
    raw = (
        "Sure, here's my plan:\n\n"
        + json.dumps(plan, ensure_ascii=False)
        + "\n\nThat should do it."
    )
    planner_response = t._lmstudio_reasoning_response(
        content="",
        reasoning_text=raw,
    )
    critic_response = t._lmstudio_reasoning_response(
        content=t._plan_critic_json(fatal=False),
        reasoning_text="ok",
    )
    executor_response = t._lmstudio_reasoning_response(
        content=json.dumps(
            {"tool_call": {"name": "read_file", "input": {"path": "x.py"}}}
        ),
        reasoning_text="read",
    )
    orchestrator, _client, _s, _st, _c = t._orchestrator(
        tmp_path, [planner_response, critic_response, executor_response]
    )

    action = await orchestrator.run(t._task("Plan"), "coding-workflow")

    assert (action.trace or {}).get("agent_status") != "failed", (
        f"workflow failed on plain-JSON-wrapped-in-prose: {action.trace!r}"
    )
