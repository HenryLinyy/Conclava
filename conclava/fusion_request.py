"""G10: Extract FusionRequest from a raw request body.

Two input shapes are supported:
  A) OpenRouter-style plugins:
       { "plugins": [{"id": "fusion", "preset": "quality"}] }
  B) Top-level fusion block (simplified):
       { "fusion": {"preset": "...", "analysis_models": [...], "judge_model": "..."} }

If both shapes are present, plugins wins (matches OpenRouter convention).
"""

from conclava.fusion_schemas import FusionRequest


def extract_fusion_request(raw_body: dict) -> FusionRequest:
    """Extract a FusionRequest from a request body dict.

    Never mutates the input. Returns an empty FusionRequest when no fusion
    override is present.
    """
    if not isinstance(raw_body, dict):
        return FusionRequest()

    # ─── Shape A: OpenRouter plugins style ────────────────────────────────
    plugins = raw_body.get("plugins")
    if isinstance(plugins, list):
        for entry in plugins:
            if isinstance(entry, dict) and entry.get("id") == "fusion":
                return FusionRequest(preset=entry.get("preset"))

    # ─── Shape B: top-level fusion block ─────────────────────────────────
    fusion_block = raw_body.get("fusion")
    if isinstance(fusion_block, dict):
        return FusionRequest(
            preset=fusion_block.get("preset"),
            analysis_models=fusion_block.get("analysis_models"),
            judge_model=fusion_block.get("judge_model"),
        )

    # ─── No override ──────────────────────────────────────────────────────
    return FusionRequest()
