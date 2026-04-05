from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from typing import Any

import orjson
from redis import asyncio as redis

from models import TaskRecord
from settings import Settings


class TaskStore:
    async def connect(self) -> None: ...

    async def close(self) -> None: ...

    async def save_task(self, record: TaskRecord) -> None: ...

    async def get_task(self, task_id: str) -> TaskRecord | None: ...

    async def append_events(self, task_id: str, events: Iterable[dict[str, Any]]) -> None: ...


class RedisTaskStore(TaskStore):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        if self._client is None:
            self._client = redis.from_url(self._settings.redis_url, decode_responses=False)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    def _task_key(self, task_id: str) -> str:
        return f"{self._settings.app_name}:task:{task_id}"

    async def save_task(self, record: TaskRecord) -> None:
        await self.connect()
        assert self._client is not None
        await self._client.set(
            self._task_key(record.task_id),
            orjson.dumps(record.model_dump(mode="json")),
            ex=self._settings.task_ttl_seconds,
        )

    async def get_task(self, task_id: str) -> TaskRecord | None:
        await self.connect()
        assert self._client is not None
        raw = await self._client.get(self._task_key(task_id))
        if raw is None:
            return None
        return TaskRecord.model_validate(orjson.loads(raw))

    async def append_events(self, task_id: str, events: Iterable[dict[str, Any]]) -> None:
        record = await self.get_task(task_id)
        if record is None:
            return
        record.events.extend(list(events))
        await self.save_task(record)


class InMemoryTaskStore(TaskStore):
    def __init__(self) -> None:
        self._tasks: dict[str, TaskRecord] = {}

    async def connect(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def save_task(self, record: TaskRecord) -> None:
        self._tasks[record.task_id] = deepcopy(record)

    async def get_task(self, task_id: str) -> TaskRecord | None:
        record = self._tasks.get(task_id)
        return deepcopy(record) if record else None

    async def append_events(self, task_id: str, events: Iterable[dict[str, Any]]) -> None:
        record = self._tasks.get(task_id)
        if record is None:
            return
        record.events.extend(list(events))

