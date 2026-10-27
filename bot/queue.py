"""Small bounded FIFO speech queue."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass(frozen=True)
class SpeechItem:
    text: str
    author_id: int


class SpeechQueue:
    def __init__(self, maxsize: int = 25) -> None:
        if maxsize < 1:
            raise ValueError("maxsize must be positive")
        self._queue: asyncio.Queue[SpeechItem | None] = asyncio.Queue(maxsize=maxsize)
        self._closed = False

    @property
    def size(self) -> int:
        return self._queue.qsize()

    @property
    def closed(self) -> bool:
        return self._closed

    async def put(self, item: SpeechItem) -> bool:
        if self._closed:
            return False
        try:
            self._queue.put_nowait(item)
        except asyncio.QueueFull:
            return False
        return True

    async def get(self) -> SpeechItem | None:
        return await self._queue.get()

    def task_done(self) -> None:
        self._queue.task_done()

    async def join(self) -> None:
        await self._queue.join()

    def close(self) -> None:
        self._closed = True
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break

