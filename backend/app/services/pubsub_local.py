"""LOCAL_DEV=1 fallback: an in-process asyncio queue standing in for the real
Pub/Sub push subscriptions. Same handler function processes messages either
way — see app/api/internal.py."""

import asyncio

from app.models import Message

_queue: asyncio.Queue[tuple[str, Message]] = asyncio.Queue()


def enqueue_local(org_id: str, message: Message) -> None:
    _queue.put_nowait((org_id, message))


async def drain_local(handler) -> None:
    """Run forever, handing each locally-enqueued message to `handler(org_id, message)`.
    Started as a background task at app startup when settings.local_dev is true."""
    while True:
        org_id, message = await _queue.get()
        try:
            await handler(org_id, message)
        finally:
            _queue.task_done()
