"""Agent profile definitions and mapping."""

from typing import Literal

ProfileName = Literal[
    "fast-agent",
    "full-agent",
    "heavy-agent",
    "chat-agent",
    "vision-fast",
    "vision-pro",
    "vision-heavy",
    "agentic-pro",
    "hermes-pro",
    "agentic-mlx",
    "formatter-mlx",
    "fusion-agent",
    "agentic-workflow",
    "coding-workflow",
    "review-workflow",
]

PROFILE_MAP_OPENAI_RESPONSES: dict[str, ProfileName] = {
    "conclava": "fast-agent",
    "conclava-fast": "fast-agent",
    "conclava-full": "full-agent",
    "conclava-heavy": "heavy-agent",
    "conclava-vision-fast": "vision-fast",
    "conclava-vision-pro": "vision-pro",
    "conclava-vision-heavy": "vision-heavy",
    "conclava-agentic-pro": "agentic-pro",
    "conclava-hermes-pro": "hermes-pro",
    "conclava-agentic-mlx": "agentic-mlx",
    "conclava-formatter-mlx": "formatter-mlx",
    "conclava-fusion": "fusion-agent",
    "conclava-fusion-budget": "fusion-agent",
    "conclava-fusion-quality": "fusion-agent",
    "conclava-fusion-coding": "fusion-agent",
    "conclava-fusion-heavy": "fusion-agent",
    "conclava-agent": "agentic-workflow",
    "conclava-code-agent": "coding-workflow",
    "conclava-review-agent": "review-workflow",
}

PROFILE_MAP_ANTHROPIC_MESSAGES: dict[str, ProfileName] = {
    "claude-conclava": "fast-agent",
    "claude-conclava-fast": "fast-agent",
    "claude-conclava-full": "full-agent",
    "claude-conclava-heavy": "heavy-agent",
    "claude-conclava-vision-fast": "vision-fast",
    "claude-conclava-vision-pro": "vision-pro",
    "claude-conclava-vision-heavy": "vision-heavy",
    "claude-conclava-agentic-pro": "agentic-pro",
    "claude-conclava-hermes-pro": "hermes-pro",
    "claude-conclava-agentic-mlx": "agentic-mlx",
    "claude-conclava-formatter-mlx": "formatter-mlx",
    "claude-conclava-fusion": "fusion-agent",
    "claude-conclava-fusion-budget": "fusion-agent",
    "claude-conclava-fusion-quality": "fusion-agent",
    "claude-conclava-fusion-coding": "fusion-agent",
    "claude-conclava-fusion-heavy": "fusion-agent",
    "claude-conclava-agent": "agentic-workflow",
    "claude-conclava-code-agent": "coding-workflow",
    "claude-conclava-review-agent": "review-workflow",
}

PROFILE_MAP_OPENAI_CHAT: dict[str, ProfileName] = {
    "conclava-chat": "chat-agent",
    "conclava-fast": "fast-agent",
    "conclava-full": "full-agent",
    "conclava-heavy": "heavy-agent",
    "conclava-vision-fast": "vision-fast",
    "conclava-vision-pro": "vision-pro",
    "conclava-vision-heavy": "vision-heavy",
    "conclava-agentic-pro": "agentic-pro",
    "conclava-hermes-pro": "hermes-pro",
    "conclava-agentic-mlx": "agentic-mlx",
    "conclava-formatter-mlx": "formatter-mlx",
    "conclava-fusion": "fusion-agent",
    "conclava-fusion-budget": "fusion-agent",
    "conclava-fusion-quality": "fusion-agent",
    "conclava-fusion-coding": "fusion-agent",
    "conclava-fusion-heavy": "fusion-agent",
    "conclava-agent": "agentic-workflow",
    "conclava-code-agent": "coding-workflow",
    "conclava-review-agent": "review-workflow",
}


def resolve_profile(
    model_name: str,
    protocol: Literal["openai_responses", "anthropic_messages", "openai_chat"],
) -> ProfileName:
    """Map a model name to the corresponding agent profile."""
    if protocol == "openai_responses":
        return PROFILE_MAP_OPENAI_RESPONSES.get(model_name, "fast-agent")
    elif protocol == "anthropic_messages":
        return PROFILE_MAP_ANTHROPIC_MESSAGES.get(model_name, "fast-agent")
    elif protocol == "openai_chat":
        return PROFILE_MAP_OPENAI_CHAT.get(model_name, "chat-agent")
    return "fast-agent"
