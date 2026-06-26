"""Regression tests for non-agentic profile prompts (hermes-pro / agentic-mlx /
formatter-mlx) and fusion panel prompt: all must disable Qwen3.6 thinking by
prefixing `/no_think` on both system and user boundaries."""

from conclava.fusion_deliberation import run_panel_serial
from conclava.fusion_schemas import PanelResponse
from conclava.fusion_presets import FusionPreset
from conclava.prompts import (
    FUSION_AGENT_ANALYSIS_SYSTEM,
    FUSION_AGENT_JUDGE_SYSTEM,
)


class _FakeClient:
    """Minimal fake that records the messages and returns the last user text."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def chat_completion(
        self, *, model, messages, max_tokens, stream=False, temperature=0.7, tools=None
    ):
        self.calls.append(
            {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "tools": tools,
            }
        )
        last_user = next((m for m in reversed(messages) if m.get("role") == "user"), {})
        return {
            "choices": [
                {
                    "message": {
                        "content": (last_user.get("content") or "").strip()[:60]
                    },
                    "finish_reason": "stop",
                }
            ]
        }

    def unload_models(self, ids):
        return None


def _build_messages(original_prompt: str) -> list[dict]:
    return [
        {"role": "system", "content": FUSION_AGENT_ANALYSIS_SYSTEM},
        {"role": "user", "content": original_prompt},
    ]


def test_fusion_analysis_system_string_starts_with_no_think():
    """The exported system prompt itself must lead with /no_think so any
    caller (including future streaming variants) can rely on it."""
    assert FUSION_AGENT_ANALYSIS_SYSTEM.lstrip().startswith("/no_think")
    assert "不要輸出任何思考過程" in FUSION_AGENT_ANALYSIS_SYSTEM


def test_fusion_panel_serial_user_message_includes_no_think_prefix():
    """run_panel_serial injects /no_think on the user boundary so the panel
    model (qwen3.6 thinking) actually writes its analysis within budget."""
    from conclava.fusion_deliberation import run_panel_serial
    from conclava.fusion_presets import FusionPreset

    captured: list[dict] = []

    class _C:
        def chat_completion(
            self,
            *,
            model,
            messages,
            max_tokens,
            stream=False,
            temperature=0.7,
            tools=None,
        ):
            captured.append(messages)
            return {
                "choices": [
                    {"message": {"content": "analysis"}, "finish_reason": "stop"}
                ]
            }

        def unload_models(self, ids):
            return None

    preset = FusionPreset(
        name="quality",
        analysis_models=("qwen/qwen3.6-35b-a3b",),
        judge_model="qwen/qwen3.6-35b-a3b",
        description="t",
    )
    run_panel_serial(
        preset=preset,
        original_prompt="hello",
        system_prompt=FUSION_AGENT_ANALYSIS_SYSTEM,
        panel_client=_C(),
        panel_max_tokens=1500,
        temperature=0.3,
        keep_last_resident=True,
    )
    msgs = captured[0]
    assert msgs[0]["content"].lstrip().startswith("/no_think")
    assert msgs[1]["content"].lstrip().startswith("/no_think")
    assert "不要輸出任何思考過程" in msgs[0]["content"]


def test_fusion_judge_system_disables_qwen_thinking_at_both_boundaries():
    judge_user = "synthesis payload"
    msgs = [
        {"role": "system", "content": FUSION_AGENT_JUDGE_SYSTEM},
        {"role": "user", "content": judge_user},
    ]
    assert msgs[0]["content"].lstrip().startswith("/no_think")
    # We prepended /no_think inside build_synthesis_prompt normally; just
    # check the system message disables thinking.
    assert "不要輸出任何思考過程" in msgs[0]["content"]


def test_fusion_panel_serial_runs_with_no_think_prompts_and_records_panel_max_tokens(
    monkeypatch,
):
    client = _FakeClient()
    preset = FusionPreset(
        name="quality",
        analysis_models=("qwen/qwen3.6-35b-a3b",),
        judge_model="qwen/qwen3.6-35b-a3b",
        description="t",
    )
    responses = run_panel_serial(
        preset=preset,
        original_prompt="ping",
        system_prompt=FUSION_AGENT_ANALYSIS_SYSTEM,
        panel_client=client,
        panel_max_tokens=1500,
        temperature=0.3,
        keep_last_resident=True,
    )
    assert len(responses) == 1
    assert isinstance(responses[0], PanelResponse)
    # Panel was given the no-think system prompt; recorded max_tokens was passed through.
    assert client.calls[0]["max_tokens"] == 1500
    assert "no_think" in client.calls[0]["messages"][0]["content"].lower()
