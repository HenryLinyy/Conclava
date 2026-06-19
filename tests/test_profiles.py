"""Tests for profile mapping."""

from conclava.profiles import resolve_profile


def test_resolve_openai_responses():
    """OpenAI Responses profile mapping."""
    assert resolve_profile("conclava", "openai_responses") == "fast-agent"
    assert resolve_profile("conclava-fast", "openai_responses") == "fast-agent"
    assert resolve_profile("conclava-full", "openai_responses") == "full-agent"
    assert resolve_profile("conclava-heavy", "openai_responses") == "heavy-agent"
    assert resolve_profile("conclava-vision-fast", "openai_responses") == "vision-fast"
    assert resolve_profile("conclava-vision-pro", "openai_responses") == "vision-pro"
    assert (
        resolve_profile("conclava-vision-heavy", "openai_responses") == "vision-heavy"
    )
    assert resolve_profile("conclava-agentic-pro", "openai_responses") == "agentic-pro"
    assert resolve_profile("conclava-hermes-pro", "openai_responses") == "hermes-pro"
    assert resolve_profile("conclava-agentic-mlx", "openai_responses") == "agentic-mlx"
    assert (
        resolve_profile("conclava-formatter-mlx", "openai_responses") == "formatter-mlx"
    )
    assert resolve_profile("conclava-fusion", "openai_responses") == "fusion-agent"


def test_resolve_anthropic_messages():
    """Anthropic Messages profile mapping."""
    assert resolve_profile("claude-conclava", "anthropic_messages") == "fast-agent"
    assert resolve_profile("claude-conclava-fast", "anthropic_messages") == "fast-agent"
    assert resolve_profile("claude-conclava-full", "anthropic_messages") == "full-agent"
    assert (
        resolve_profile("claude-conclava-heavy", "anthropic_messages") == "heavy-agent"
    )
    assert (
        resolve_profile("claude-conclava-vision-fast", "anthropic_messages")
        == "vision-fast"
    )
    assert (
        resolve_profile("claude-conclava-vision-pro", "anthropic_messages")
        == "vision-pro"
    )
    assert (
        resolve_profile("claude-conclava-vision-heavy", "anthropic_messages")
        == "vision-heavy"
    )
    assert (
        resolve_profile("claude-conclava-agentic-pro", "anthropic_messages")
        == "agentic-pro"
    )
    assert (
        resolve_profile("claude-conclava-hermes-pro", "anthropic_messages")
        == "hermes-pro"
    )
    assert (
        resolve_profile("claude-conclava-agentic-mlx", "anthropic_messages")
        == "agentic-mlx"
    )
    assert (
        resolve_profile("claude-conclava-formatter-mlx", "anthropic_messages")
        == "formatter-mlx"
    )
    assert (
        resolve_profile("claude-conclava-fusion", "anthropic_messages")
        == "fusion-agent"
    )


def test_resolve_openai_chat():
    """OpenAI Chat profile mapping."""
    assert resolve_profile("conclava-chat", "openai_chat") == "chat-agent"
    assert resolve_profile("conclava-fast", "openai_chat") == "fast-agent"
    assert resolve_profile("conclava-full", "openai_chat") == "full-agent"
    assert resolve_profile("conclava-heavy", "openai_chat") == "heavy-agent"
    assert resolve_profile("conclava-vision-fast", "openai_chat") == "vision-fast"
    assert resolve_profile("conclava-vision-pro", "openai_chat") == "vision-pro"
    assert resolve_profile("conclava-vision-heavy", "openai_chat") == "vision-heavy"
    assert resolve_profile("conclava-agentic-pro", "openai_chat") == "agentic-pro"
    assert resolve_profile("conclava-hermes-pro", "openai_chat") == "hermes-pro"
    assert resolve_profile("conclava-agentic-mlx", "openai_chat") == "agentic-mlx"
    assert resolve_profile("conclava-formatter-mlx", "openai_chat") == "formatter-mlx"
    assert resolve_profile("conclava-fusion", "openai_chat") == "fusion-agent"


def test_unknown_model():
    """Unknown model name should default to fast-agent."""
    assert resolve_profile("unknown-model", "openai_responses") == "fast-agent"
    assert resolve_profile("unknown-model", "anthropic_messages") == "fast-agent"
    assert resolve_profile("unknown-model", "openai_chat") == "chat-agent"
