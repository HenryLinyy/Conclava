"""Conclava SDK — Python client for the Conclava v1.5.

Public surface:
    from conclava_sdk import ConclavaClient, FusionPreset, FusionEvent

    client = ConclavaClient("http://127.0.0.1:8088")

    # Non-streaming
    result = client.fusion_chat(
        messages=[{"role": "user", "content": "Compare sort algorithms"}],
        preset=FusionPreset.QUALITY,
    )
    print(result.text)
    print(result.panel_models)
    print(result.judge_model)

    # Streaming (sync generator)
    for event in client.fusion_chat_stream(
        messages=[{"role": "user", "content": "..."}],
        preset=FusionPreset.BUDGET,
    ):
        if event.event == "judge_token":
            print(event.delta, end="", flush=True)
        elif event.event == "final":
            print()

    # Async variant
    result = await client.afusion_chat(
        messages=[{"role": "user", "content": "..."}],
        preset=FusionPreset.CODING,
    )
"""

from conclava_sdk.client import ConclavaClient
from conclava_sdk.events import (
    FusionEvent,
    PanelEvent,
    JudgeEvent,
    FinalEvent,
    ErrorEvent,
)
from conclava_sdk.types import (
    FusionPreset,
    FusionPresetName,
    FusionResult,
)


__all__ = [
    "ConclavaClient",
    "FusionEvent",
    "PanelEvent",
    "JudgeEvent",
    "FinalEvent",
    "ErrorEvent",
    "FusionPreset",
    "FusionPresetName",
    "FusionResult",
]
