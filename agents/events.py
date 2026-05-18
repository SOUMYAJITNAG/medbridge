"""Event bus for streaming agent pipeline progress to the frontend via SSE."""

from __future__ import annotations
import asyncio
from collections import defaultdict
from typing import Any


class EventBus:
    """Thread-safe event bus: agents publish → SSE endpoint consumes."""

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self._done: set[str] = set()

    def publish(self, run_id: str, event: dict[str, Any]) -> None:
        """Publish an event for a given pipeline run."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.call_soon_threadsafe(self._queues[run_id].put_nowait, event)
            else:
                self._queues[run_id].put_nowait(event)
        except Exception:
            self._queues[run_id].put_nowait(event)

    async def consume(self, run_id: str):
        """Async generator that yields events for the given run_id."""
        q = self._queues[run_id]
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=30.0)
                yield event
                if event.get("type") == "pipeline_done" or event.get("type") == "pipeline_error":
                    break
            except asyncio.TimeoutError:
                yield {"type": "heartbeat"}
                if run_id in self._done:
                    break

    def mark_done(self, run_id: str) -> None:
        self._done.add(run_id)

    def cleanup(self, run_id: str) -> None:
        self._queues.pop(run_id, None)
        self._done.discard(run_id)


# Singleton event bus shared across the app
bus = EventBus()
