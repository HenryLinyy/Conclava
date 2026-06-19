"""Streaming helpers for keepalive and event delivery."""

from typing import AsyncGenerator
import json
import asyncio
import logging

logger = logging.getLogger("conclava.streaming")


def sse_event(
    data: dict | list | str | None = None,
    event: str | None = None,
    comment: str | None = None,
) -> str:
    """Format one server-sent event frame."""
    if comment is not None:
        return f": {comment}\n\n"

    lines: list[str] = []
    if event:
        lines.append(f"event: {event}")
    if isinstance(data, str):
        encoded = data
    else:
        encoded = json.dumps(data if data is not None else {}, ensure_ascii=False)
    lines.append(f"data: {encoded}")
    return "\n".join(lines) + "\n\n"


async def keepalive_stream(
    event_generator: AsyncGenerator[dict, None],
    keepalive_seconds: int = 10,
) -> AsyncGenerator[str, None]:
    """Wrap an event generator with keepalive pings.

    Sends a keepalive event every `keepalive_seconds` if no real event
    has been sent in that window.
    """
    async for event in event_generator:
        yield f"data: {json.dumps(event)}\n\n"
        # Reset keepalive timer after each real event
        await asyncio.sleep(0)

    # After final event, send done signal
    yield "data: [DONE]\n\n"


async def keepalive_task(keepalive_seconds: int, event_queue: asyncio.Queue):
    """Background task that sends keepalive pings at regular intervals."""
    while True:
        await asyncio.sleep(keepalive_seconds)
        await event_queue.put({"type": "keepalive", "data": {}})


async def stream_with_keepalive(
    event_generator: AsyncGenerator[dict, None],
    keepalive_seconds: int = 10,
) -> AsyncGenerator[str, None]:
    """Stream events with keepalive pings from a background task."""
    event_queue: asyncio.Queue = asyncio.Queue()

    async def producer():
        async for event in event_generator:
            await event_queue.put(event)

    keepalive_task_handle = asyncio.create_task(
        keepalive_task(keepalive_seconds, event_queue)
    )

    # Run producer in background
    producer_task = asyncio.create_task(producer())

    while True:
        done_tasks = [producer_task, keepalive_task_handle]
        done, _ = await asyncio.wait(
            done_tasks,
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in done:
            if task == producer_task and task.exception():
                raise task.exception()
        # If producer is done and queue is empty, we're done
        if producer_task.done() and event_queue.empty():
            break

        # Get next event
        try:
            event = await asyncio.wait_for(
                event_queue.get(), timeout=keepalive_seconds + 2
            )
            yield f"data: {json.dumps(event)}\n\n"
        except asyncio.TimeoutError:
            continue

    keepalive_task_handle.cancel()
    yield "data: [DONE]\n\n"
