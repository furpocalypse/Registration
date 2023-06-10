"""Hook service."""
import asyncio
from asyncio import CancelledError, Task
from collections.abc import Iterable
from datetime import datetime
from typing import Any, Optional, Union, cast
from uuid import UUID

from loguru import logger
from oes.hook import ExecutableHookConfig, HttpHookConfig, PythonHookConfig
from oes.registration.database import DBConfig
from oes.registration.entities.hook import HookLogEntity
from oes.registration.http_client import get_http_client
from oes.registration.serialization.json import json_dumps, json_loads
from oes.registration.util import get_now
from sqlalchemy.ext.asyncio import AsyncSession

HookConfig = Union[
    PythonHookConfig,
    HttpHookConfig,
    ExecutableHookConfig,
]

# TODO: rewrite


async def http_func(body: Any, config: HttpHookConfig) -> Any:
    client = get_http_client()
    hook = cast(HttpHook, config.hook)
    res = await client.post(
        hook.url,
        content=json_dumps(body),
        headers={
            "Content-Type": "application/json",
        },
    )
    res.raise_for_status()

    body = res.read()
    if not body:
        return None

    return json_loads(body)


class HookRetryService:
    tasks: set[Task]

    def __init__(self, db_config: DBConfig):
        self.db_config = db_config
        self.tasks = set()

    async def _retry(self, id: UUID):
        session = self.db_config.session_factory()
        try:
            service = HookService(self, session)
            await service.invoke_hooks(id)
        finally:
            await session.close()

    async def _wait_and_retry(self, id: UUID, retry: datetime):
        now = get_now()
        while now < retry:
            diff = (retry - now).total_seconds()
            await asyncio.sleep(diff)
            now = get_now()

        await self._retry(id)

    def retry_hook_at(self, id: UUID, retry: datetime):
        """Retry the given hook ID at a later time."""

        loop = asyncio.get_running_loop()
        task = loop.create_task(self._wait_and_retry(id, retry))
        task.add_done_callback(lambda t: self.tasks.remove(t))
        self.tasks.add(task)

    async def close(self):
        """Cancel all tasks."""
        tasks = list(self.tasks)
        for task in tasks:
            task.cancel()
            try:
                await task
            except CancelledError:
                pass


class HookService:
    """Hook service."""

    def __init__(self, retry_service: HookRetryService, db: AsyncSession):
        # TODO: check executable/python hooks against config
        self.retry_service = retry_service
        self.db = db

    async def get_hook_entity(self, id: UUID) -> Optional[HookLogEntity]:
        """Get a :class:`HookLogEntity` by ID."""
        res = await self.db.get(HookLogEntity, id, with_for_update=True)
        return res

    async def invoke_hook(self, entity: HookLogEntity):
        """Attempt to invoke a hook.

        Updates retry count/time if it fails.
        """
        hook = entity.get_hook()
        options = InvokeOptions(hook, self.get_config())

        try:
            await hook.invoke(entity.body, options)
        except Exception:
            retry_at = entity.update_attempts()
            await self.db.flush()

            if retry_at is not None:
                self.retry_service.retry_hook_at(entity.id, retry_at)

            retry_msg = (
                f"Will retry at {retry_at}"
                if retry_at is not None
                else "Will not retry"
            )
            logger.opt(exception=True).error(f"Hook failed. {retry_msg}.")
        else:
            logger.debug(f"Called hook {hook}")
            await self.db.delete(entity)
            await self.db.flush()

    async def create(self, hook: HookConfig, body: dict[str, Any]) -> UUID:
        """Create a hook entity.

        Returns:
            The created hook ID.
        """
        entity = HookLogEntity.create(hook, body)
        self.db.add(entity)
        await self.db.flush()
        return entity.id

    async def invoke_hooks(self, ids: Union[UUID, Iterable[UUID]]):
        """Attempt to invoke the given hook IDs.

        Silently skips each ID that is not found/not retryable. Commits the DB
        transaction after each hook is tried.

        Args:
            ids: The ID or IDs to send.
        """
        ids = [ids] if isinstance(ids, UUID) else ids
        for id in ids:
            obj = await self.get_hook_entity(id)
            if obj and obj.get_is_retryable():
                await self.invoke_hook(obj)
                await self.db.commit()
