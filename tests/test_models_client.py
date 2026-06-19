"""Tests for local model backend client compatibility shims."""

from unittest.mock import MagicMock, patch

from conclava.models import OllamaClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_lmstudio_native_chat_fallback_uses_openai_multimodal_shape():
    """LM Studio has OpenAI-compatible chat, not Ollama /api/chat.

    The compatibility client should translate the native Ollama image-message shape
    used by VisionProcessor into OpenAI multimodal content and return a native-like
    {"message": ...} payload to keep the rest of the gateway unchanged.
    """
    client = OllamaClient(
        "http://127.0.0.1:1234/v1",
        backend="lmstudio",
        lmstudio_cli_path="/Users/yourname/.lmstudio/bin/lms",
    )
    client.client.post = MagicMock(
        return_value=FakeResponse(
            {"choices": [{"message": {"role": "assistant", "content": "Summary: UI"}}]}
        )
    )

    result = client.native_chat_completion(
        model="qwen/qwen3-vl-30b",
        messages=[
            {"role": "system", "content": "extract evidence"},
            {"role": "user", "content": "OCR this", "images": ["aW1hZ2U="]},
        ],
        max_tokens=100,
        temperature=0.0,
        think=False,
    )

    assert result == {"message": {"role": "assistant", "content": "Summary: UI"}}
    url = client.client.post.call_args.args[0]
    payload = client.client.post.call_args.kwargs["json"]
    assert url == "http://127.0.0.1:1234/v1/chat/completions"
    assert payload["model"] == "qwen/qwen3-vl-30b"
    assert payload["max_tokens"] == 100
    assert payload["temperature"] == 0.0
    assert payload["messages"][1]["content"] == [
        {"type": "text", "text": "OCR this"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,aW1hZ2U="}},
    ]
    assert "think" not in payload


def test_lmstudio_unload_models_uses_lms_unload_all():
    client = OllamaClient(
        "http://127.0.0.1:1234/v1",
        backend="lmstudio",
        lmstudio_cli_path="/Users/yourname/.lmstudio/bin/lms",
    )
    client.client.post = MagicMock()

    with patch("conclava.models.subprocess.run") as run:
        client.unload_models(["qwen/qwen3-coder-next", "google/gemma-4-26b-a4b-qat"])

    run.assert_called_once_with(
        ["/Users/yourname/.lmstudio/bin/lms", "unload", "--all"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    client.client.post.assert_not_called()
