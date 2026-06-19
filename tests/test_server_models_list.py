"""Tests for advertised gateway model aliases."""

from conclava.server import MODELS_LIST


def test_models_list_advertises_v15_profiles():
    ids = {item["id"] for item in MODELS_LIST["data"]}

    assert {
        "conclava-vision-fast",
        "conclava-vision-pro",
        "conclava-vision-heavy",
        "conclava-agentic-pro",
        "conclava-hermes-pro",
        "conclava-agentic-mlx",
        "conclava-formatter-mlx",
        "claude-conclava-vision-fast",
        "claude-conclava-vision-pro",
        "claude-conclava-vision-heavy",
        "claude-conclava-agentic-pro",
        "claude-conclava-hermes-pro",
        "claude-conclava-agentic-mlx",
        "claude-conclava-formatter-mlx",
    }.issubset(ids)


def test_models_list_advertises_g10_fusion_profiles():
    """G10: OpenRouter-style fusion deliberation router model ids."""
    ids = {item["id"] for item in MODELS_LIST["data"]}

    assert "conclava-fusion" in ids
    assert "claude-conclava-fusion" in ids
