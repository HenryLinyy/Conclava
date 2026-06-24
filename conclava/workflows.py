"""Static workflow stage-to-model-role maps."""


from conclava.model_roles import ModelRole, WorkflowName, WorkflowStage


# v1.7 stage map (kept for backward compat — used by ModelSelector.select()).
WORKFLOW_STAGE_ROLE_MAP: dict[str, dict[str, ModelRole]] = {
    WorkflowName.AGENTIC.value: {
        WorkflowStage.CONTEXT.value: ModelRole.PLANNER,
        WorkflowStage.PLANNER.value: ModelRole.PLANNER,
        WorkflowStage.PLAN_CRITIC.value: ModelRole.CRITIC,
        WorkflowStage.EXECUTOR.value: ModelRole.EXECUTOR,
        WorkflowStage.JUDGE.value: ModelRole.JUDGE,
        WorkflowStage.FINALIZER.value: ModelRole.JUDGE,
    },
    WorkflowName.CODING.value: {
        WorkflowStage.CONTEXT.value: ModelRole.PLANNER,
        WorkflowStage.PLANNER.value: ModelRole.PLANNER,
        WorkflowStage.PLAN_CRITIC.value: ModelRole.CRITIC,
        WorkflowStage.EXECUTOR.value: ModelRole.EXECUTOR,
        WorkflowStage.TEST.value: ModelRole.EXECUTOR,
        WorkflowStage.REPAIR.value: ModelRole.REPAIR,
        WorkflowStage.JUDGE.value: ModelRole.JUDGE,
        WorkflowStage.FINALIZER.value: ModelRole.JUDGE,
    },
    WorkflowName.REVIEW.value: {
        WorkflowStage.CONTEXT.value: ModelRole.PLANNER,
        WorkflowStage.REVIEWER.value: ModelRole.CRITIC,
        WorkflowStage.JUDGE.value: ModelRole.JUDGE,
        WorkflowStage.FINALIZER.value: ModelRole.JUDGE,
    },
}


# v1.8: finer-grained stage map (per plan §8). Each stage picks exactly one
# ModelRole. Selection of the *model* is handled by ModelSelector based on
# the role + Qwable/Qwythos enable flags.
STAGE_ROLE_MAP: dict[WorkflowStage, ModelRole] = {
    # Long-context stages — Qwythos optional primary, qwen3.6 default.
    WorkflowStage.CONTEXT_ACQUISITION: ModelRole.LONG_CONTEXT_WORKER,
    WorkflowStage.REPO_INDEX: ModelRole.LONG_CONTEXT_WORKER,
    WorkflowStage.CONTEXT_COMPACTION: ModelRole.LONG_CONTEXT_WORKER,
    # Planning — unchanged from v1.7.
    WorkflowStage.PLAN_REVIEW: ModelRole.CRITIC,
    WorkflowStage.PLAN_REVISION: ModelRole.PLANNER,
    # Execution / repair — Qwable primary, qwen3-coder-next fallback.
    WorkflowStage.EXECUTE_PATCH: ModelRole.EXECUTOR,
    WorkflowStage.REPAIR_PATCH: ModelRole.REPAIR,
    # Failure analysis — long context (read tool result + error tail).
    WorkflowStage.FAILURE_ANALYSIS: ModelRole.LONG_CONTEXT_WORKER,
    # Final stages — judge (unchanged).
    WorkflowStage.FINAL_REVIEW: ModelRole.JUDGE,
    WorkflowStage.FINAL_REPORT: ModelRole.JUDGE,
}


WORKFLOW_DEFAULT_MAX_TOKENS: dict[str, dict[str, int]] = {
    # Reasoning-model budget sizing (qwen3.6-35b-a3b as planner / judge /
    # critic; deepseek-r1-distill-qwen-32b as critic). These models emit a
    # chain-of-thought block in `reasoning_content` BEFORE the final
    # structured output, so the budget must cover both. Empirically the
    # planner can spend ~1.8k-2.5k reasoning tokens + ~1.1k-2.4k output
    # chars for the JSON plan on trivial tasks. 3000 still produced
    # `finish_reason=length` and partial JSON for the Fibonacci code-agent
    # prompt, while 4000 completed and parsed successfully. The previous
    # 1200 budget caused every planner call to land at `finish_reason=length`
    # with empty or partial `content`, which surfaced to users as
    # `planner_json_parse_failed`.
    WorkflowName.AGENTIC.value: {
        WorkflowStage.PLANNER.value: 4000,
        WorkflowStage.PLAN_CRITIC.value: 2500,
        WorkflowStage.EXECUTOR.value: 2000,
        WorkflowStage.JUDGE.value: 2500,
        WorkflowStage.FINALIZER.value: 2500,
    },
    WorkflowName.CODING.value: {
        WorkflowStage.PLANNER.value: 4000,
        WorkflowStage.PLAN_CRITIC.value: 2500,
        WorkflowStage.EXECUTOR.value: 2500,
        WorkflowStage.REPAIR.value: 2500,
        WorkflowStage.JUDGE.value: 2500,
        WorkflowStage.FINALIZER.value: 2500,
    },
    WorkflowName.REVIEW.value: {
        WorkflowStage.REVIEWER.value: 2500,
        WorkflowStage.JUDGE.value: 2500,
        WorkflowStage.FINALIZER.value: 2500,
    },
}
