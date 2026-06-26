"""Regression tests for agent workflow token budgets."""

from conclava.model_roles import WorkflowName, WorkflowStage
from conclava.workflows import WORKFLOW_DEFAULT_MAX_TOKENS


def test_planner_budget_allows_reasoning_model_to_finish_json_plan():
    """Qwen3.6 planner can spend ~1.8k-2.5k tokens on reasoning.

    With a 3000-token budget, LM Studio often returned finish_reason=length and
    content ended as partial JSON, causing planner_json_parse_failed. Direct
    reproduction with the Fibonacci code-agent prompt succeeded at 4000 tokens.
    """
    assert (
        WORKFLOW_DEFAULT_MAX_TOKENS[WorkflowName.AGENTIC.value][
            WorkflowStage.PLANNER.value
        ]
        >= 4000
    )
    assert (
        WORKFLOW_DEFAULT_MAX_TOKENS[WorkflowName.CODING.value][
            WorkflowStage.PLANNER.value
        ]
        >= 4000
    )
