"""v1.10 regression: agentic-pro / hermes-pro / agentic-mlx must use
gemma (not qwen3.6) because the latter returns empty content on the
first call after `lms unload -a`. We accept losing qwen3.6 reasoning
on these profiles in exchange for live-matrix stability."""

from conclava.config import FusionConfig


def test_v110_agentic_pro_uses_gemma_for_first_call_stability():
    cfg = FusionConfig()
    assert cfg.model_agentic_pro == "google/gemma-4-26b-a4b-qat"


def test_v110_hermes_pro_uses_gemma_for_first_call_stability():
    cfg = FusionConfig()
    assert cfg.model_hermes_pro == "google/gemma-4-26b-a4b-qat"


def test_v110_agentic_mlx_uses_gemma_for_first_call_stability():
    cfg = FusionConfig()
    assert cfg.model_agentic_mlx == "google/gemma-4-26b-a4b-qat"
