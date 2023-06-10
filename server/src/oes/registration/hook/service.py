"""Hook service module."""
import asyncio
import contextlib
from asyncio import BaseEventLoop, CancelledError, Task, get_running_loop
from datetime import datetime
from inspect import iscoroutinefunction
from typing import Any, Iterable, Optional, Union
from uuid import UUID

import sqlalchemy.event
from loguru import logger
from oes.registration.database import DBConfig
from oes.registration.hook.entities import HookLogEntity
from oes.registration.hook.models import HookConfig, HookConfigEntry, HookEvent
from oes.registration.util import get_now
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class HookRetryService:
    """Service that manages retrying failed hooks."""

    _tasks: set[Task]
    _post_commit_hooks: dict[
        int, list[Union[UUID, tuple[HookConfigEntry, dict[str, Any]]]]
    ]

    def __init__(self, loop: BaseEventLoop, db_config: DBConfig):
        self._loop = loop
        self._db_config = db_config
        self._tasks = set()
        self._post_commit_hooks = {}
        sqlalchemy.event.listen(
            self._db_config.session_factory, "after_commit", self._handle_post_commit
        )
        sqlalchemy.event.listen(
            self._db_config.session_factory,
            "after_rollback",
            self._handle_post_rollback,
        )

    def _handle_post_commit(self, session: AsyncSession):
        """Schedule invocation of all hooks associated with the committed session."""
        hooks = self._post_commit_hooks.pop(id(session), [])
        entity_ids = [h for h in hooks if isinstance(h, UUID)]
        hook_objs = [h for h in hooks if isinstance(h, tuple)]

        # messy

        if entity_ids:
            task = self._loop.create_task(
                attempt_invoke_hooks(entity_ids, self, self._db_config.session_factory)
            )
            task.add_done_callback(lambda t: self._tasks.remove(t))
            self._tasks.add(task)

        for hook_config, body in hook_objs:

            async def _run():
                try:
                    await invoke_hook(hook_config, body)
                except Exception:
                    logger.opt(exception=True).error(
                        f"Hook {hook_config} failed. Will not retry."
                    )

            task = self._loop.create_task(_run())
            task.add_done_callback(lambda t: self._tasks.remove(t))
            self._tasks.add(task)

    def _handle_post_rollback(self, session: AsyncSession):
        """Discard all scheduled hooks if a session rollbacks."""
        self._post_commit_hooks.pop(id(session))

    def invoke_hook_after_commit(
        self,
        id_or_config: Union[UUID, tuple[HookConfigEntry, dict[str, Any]]],
        session: AsyncSession,
    ):
        """Schedule a hook to be invoked after the given session commits.

        Args:
            id_or_config: A hook entity ID or a tuple of a config and body.
            session: The DB session.
        """
        list_ = self._post_commit_hooks.setdefault(id(session), [])
        list_.append(id_or_config)

    async def _wait_and_retry(self, id: UUID, retry: datetime):
        now = get_now()
        while now < retry:
            diff = (retry - now).total_seconds()
            await asyncio.sleep(diff)
            now = get_now()

        await attempt_invoke_hooks([id], self, self._db_config.session_factory)

    def retry_hook_at(self, id: UUID, retry: datetime):
        """Retry the given hook ID at a later time."""
        loop = asyncio.get_running_loop()
        task = loop.create_task(self._wait_and_retry(id, retry))
        task.add_done_callback(lambda t: self._tasks.remove(t))
        self._tasks.add(task)

    async def close(self):
        """Cancel all tasks."""
        sqlalchemy.event.remove(
            self._db_config.session_factory,
            "after_rollback",
            self._handle_post_rollback,
        )
        sqlalchemy.event.remove(
            self._db_config.session_factory, "after_commit", self._handle_post_commit
        )
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
            with contextlib.suppress(CancelledError):
                await task


class HookService:
    """Service that manages creating/invoking hooks."""

    def __init__(self, retry_service: HookRetryService, db: AsyncSession):
        # TODO: check executable/python hooks against config
        self.retry_service = retry_service
        self.db = db

    async def get_hook_entity(self, id: UUID) -> Optional[HookLogEntity]:
        """Get a :class:`HookLogEntity` by ID."""
        res = await self.db.get(HookLogEntity, id, with_for_update=True)
        return res

    async def create(self, hook_config: HookConfigEntry, body: dict[str, Any]) -> UUID:
        """Create a hook entity.

        Returns:
            The created hook ID.
        """
        entity = HookLogEntity.create(hook_config, body)
        self.db.add(entity)
        await self.db.flush()
        return entity.id


async def schedule_hooks_for_event(
    service: HookService,
    config: HookConfig,
    hook_event: HookEvent,
    body: dict[str, Any],
):
    """Schedule hooks for the given event to be called after the transaction commits.

    Args:
        service: The :class:`HookService`.
        config: The :class:`HookConfig`.
        hook_event: The event.
        body: The hook body.
    """
    for hook_config in config.get_by_event(hook_event):
        if hook_config.retry:
            id_ = await service.create(hook_config, body)
            service.retry_service.invoke_hook_after_commit(id_, service.db)
        else:
            service.retry_service.invoke_hook_after_commit(
                (hook_config, body), service.db
            )


async def attempt_invoke_hooks(
    ids: Iterable[UUID],
    retry_service: HookRetryService,
    db_factory: async_sessionmaker,
):
    """Attempt to invoke the hooks with the given IDs.

    Silently skips hooks that do not exist or are not retryable.

    Schedules the hooks to be retried if an exception occurs.

    Args:
        ids: The hook IDs.
        retry_service: The :class:`HookRetryService`.
        db_factory: The DB session factory.
    """
    session = db_factory()
    try:
        service = HookService(retry_service, session)

        for id_ in ids:
            entity = await service.get_hook_entity(id_)
            if entity and entity.get_is_retryable():
                try:
                    await attempt_invoke_hook_entity(entity, retry_service)
                except Exception:
                    # ignore exceptions
                    await session.commit()
                else:
                    await session.delete(entity)
                    await session.commit()
    finally:
        await session.close()


async def attempt_invoke_hook_entity(
    entity: HookLogEntity,
    retry_service: HookRetryService,
) -> Any:
    """Attempt to invoke the hook described by a :class:`HookLogEntity`.

    If an exception occurs, the entity will be scheduled to be retried and the
    exception will be re-raised.

    Args:
        entity: The :class:`HookLogEntity`.
        retry_service: The :class:`HookRetryService`.
    """
    try:
        result = await invoke_hook_entity(entity)
    except Exception:
        retry_at = entity.update_attempts()
        if retry_at is not None:
            retry_service.retry_hook_at(entity.id, retry_at)
            retry_msg = f"Will retry at {retry_at}"
        else:
            retry_msg = "Will not retry"

        logger.opt(exception=True).error(f"Hook {entity} failed. {retry_msg}.")
        raise
    else:
        logger.debug(f"Called hook {entity}")
        return result


async def invoke_hook_entity(entity: HookLogEntity) -> Any:
    """Invoke the hook described by a :class:`HookLogEntity`."""
    hook_config = entity.get_config_entry()
    body = entity.body
    return await invoke_hook(hook_config, body)


async def invoke_hook(hook_config: HookConfigEntry, body: dict[str, Any]) -> Any:
    """Invoke a hook with the given body.

    Args:
        hook_config: The :class:`HookConfigEntry` representing the hook to invoke.
        body: The body.

    Returns:
        The returned body.
    """
    hook = hook_config.get_hook()
    if iscoroutinefunction(hook):
        return await hook(body)
    else:
        loop = get_running_loop()
        return await loop.run_in_executor(None, hook, body)
