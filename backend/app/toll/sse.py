"""Thread-safe Server-Sent-Events broker for the toll live feed.

The ingest hook runs in a worker thread (sync endpoint), while SSE responses
are async generators on the event loop, so the handoff must be thread-safe.
Each subscriber owns a ``queue.Queue``; ``broadcast`` fan-outs to all of them,
and the async generator drains its queue with a short poll + keepalive.
"""

import asyncio
import json
import queue
from typing import Any

_subscribers: set[queue.Queue] = set()


def broadcast(event: str, payload: Any) -> None:
    """Push an event to every connected client. Safe to call from any thread."""
    line = f"event: {event}\ndata: {json.dumps(payload, default=str)}\n\n"
    for q in list(_subscribers):
        try:
            q.put_nowait(line)
        except queue.Full:
            pass


async def event_stream():
    """Async generator yielding SSE frames for one subscriber."""
    q: queue.Queue = queue.Queue(maxsize=1000)
    _subscribers.add(q)
    try:
        yield "retry: 3000\n\n"
        idle = 0
        while True:
            try:
                while True:
                    yield q.get_nowait()
                    idle = 0
            except queue.Empty:
                pass
            await asyncio.sleep(0.25)
            idle += 1
            if idle >= 60:  # ~15s keepalive comment
                idle = 0
                yield ": ka\n\n"
    finally:
        _subscribers.discard(q)
