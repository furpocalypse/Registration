"""Hook service module."""
import asyncio
import contextlib
from asyncio import AbstractEventLoop, CancelledError, Task, get_running_loop
from collections.abc import Awaitable, Callable
from concurrent.futures import Future
from datetime import datetime
from functools import partial, wraps
from inspect import iscoroutinefunction
from typing import Any, Iterable, Optional, TypeVar
from uuid import UUID

import sqlalchemy.event
from loguru import logger
from oes.registration.hook.entities import HookLogEntity
from oes.registration.hook.models import HookConfig, HookConfigEntry, HookEvent
from oes.registration.serialization import get_converter
from oes.registration.util import get_now
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session
from typing_extensions import ParamSpec

P = ParamSpec("P")
R = TypeVar("R", covariant=True)


class CommitCallbackService:
    """Run callbacks when a DB session commits."""

    # this might be useful enough to move into its own module

    _callbacks: dict[int, list[Callable[[], Awaitable[None]]]]

    def __init__(self, loop: AbstractEventLoop):
        self._loop = loop
        self._callbacks = {}

    def _on_commit(self, session: Session) -> Future:
        obj_id = id(session)
        return asyncio.run_coroutine_threadsafe(
            self._execute_callbacks(obj_id), self._loop
        )

    def _on_rollback(self, session: Session) -> Future:
        obj_id = id(session)
        return asyncio.run_coroutine_threadsafe(
            self._discard_callbacks(obj_id), self._loop
        )

    def add_listeners(self, event_target: async_sessionmaker):
        underlying = event_target.class_.sync_session_class
        sqlalchemy.event.listen(underlying, "after_commit", self._on_commit)
        sqlalchemy.event.listen(underlying, "after_rollback", self._on_rollback)

    def remove_listeners(self, event_target: async_sessionmaker):
        underlying = event_target.class_.sync_session_class
        sqlalchemy.event.remove(underlying, "after_rollback", self._on_rollback)
        sqlalchemy.event.remove(underlying, "after_commit", self._on_commit)

    def add_callback(
        self,
        session: AsyncSession,
        func: Callable[P, R],
        *args: P.args,
        **kwargs: P.kwargs,
    ):
        """Add a function to call when the session commits.

        Warning:
            This is not thread-safe and must be called from within the event loop.
        """
        obj_id = id(session.sync_session)
        bound = partial(func, *args, **kwargs)
        list_ = self._callbacks.setdefault(obj_id, [])
        list_.append(bound)  # type: ignore

    async def _execute_callbacks(self, obj_id: int):
        callbacks = self._callbacks.pop(obj_id, [])
        if not callbacks:
            return

        tasks = [_suppress_exceptions(cb)() for cb in callbacks]
        await asyncio.gather(*tasks)

    async def _discard_callbacks(self, obj_id: int):
        self._callbacks.pop(obj_id, None)


def _suppress_exceptions(
    func: Callable[P, Awaitable[None]]
) -> Callable[P, Awaitable[None]]:
    @wraps(func)
    async def wrapped(*args: P.args, **kwargs: P.kwargs):
        try:
            await func(*args, **kwargs)
        except Exception:
            logger.opt(exception=True).error(
                "Unhandled exception in post-commit callback"
            )

    return wrapped


class HookRetryService:
    """Service that manages scheduling retries of hooks."""

    _tasks: set[Task]

    def __init__(
        self,
        loop: AbstractEventLoop,
        config: HookConfig,
        session_factory: async_sessionmaker,
    ):
        self._loop = loop
        self.config = config
        self._tasks = set()
        self._session_factory = session_factory

    def retry_hook_id_at(self, t: datetime, id: UUID) -> Task:
        """Attempt to retry the hook ID at a later time.

        Warning:
            This method is not thread-safe and should only be called from the event
            loop.

        Args:
            t: When to retry the hook.
            id: The hook ID.
        """
        coro = _call_at(
            t,
            attempt_invoke_hooks,
            [id],
            self,
            self._session_factory,
            self.config,
        )
        task = self._loop.create_task(coro)
        task.add_done_callback(lambda t: self._tasks.remove(t))
        self._tasks.add(task)
        return task

    async def close(self):
        """Cancel all tasks."""
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()

        for task in tasks:
            with contextlib.suppress(CancelledError):
                await task


async def _call_at(
    t: datetime, func: Callable[P, Awaitable[None]], *args: P.args, **kwargs: P.kwargs
) -> None:
    """Wait until the given time and then call the function."""
    await _wait_until(t)
    await func(*args, **kwargs)


async def _wait_until(t: datetime):
    """Wait until the given time."""
    now = get_now()
    while now < t:
        diff = (t - now).total_seconds()
        await asyncio.sleep(diff)
        now = get_now()


class HookService:
    """Service that manages creating/retrieving hooks."""

    def __init__(self, db: AsyncSession):
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


class HookSender:
    """Utility class for invoking hooks for an event."""

    def __init__(
        self,
        config: HookConfig,
        db_factory: async_sessionmaker,
        db: AsyncSession,
        service: HookService,
        retry_service: HookRetryService,
        callback_service: CommitCallbackService,
    ):
        self.config = config
        self.db_factory = db_factory
        self.db = db
        self.service = service
        self.retry_service = retry_service
        self.callback_service = callback_service

    async def schedule_hooks_for_event(
        self,
        hook_event: HookEvent,
        body: Any,
    ):
        """Invoke hooks for the given event after the transaction commits.

        Args:
            hook_event: The event.
            body: The hook body.
        """
        body_dict = (
            body if isinstance(body, dict) else get_converter().unstructure(body)
        )

        for hook_config in self.config.get_by_event(hook_event):
            if hook_config.retry:
                hook_id = await self.service.create(hook_config, body_dict)
                self.callback_service.add_callback(
                    self.db,
                    attempt_invoke_hooks,
                    [hook_id],
                    self.retry_service,
                    self.db_factory,
                    self.config,
                )
            else:
                self.callback_service.add_callback(
                    self.db, invoke_hook, hook_config, body_dict
                )


async def attempt_invoke_hooks(
    ids: Iterable[UUID],
    retry_service: HookRetryService,
    db_factory: async_sessionmaker,
    hook_config: HookConfig,
):
    """Attempt to invoke the hooks with the given IDs.

    Silently skips hooks that do not exist or are not retryable.

    Schedules the hooks to be retried if an exception occurs.

    Args:
        ids: The hook IDs.
        retry_service: The :class:`HookRetryService`.
        db_factory: The DB session factory.
        hook_config: The hook configuration.
    """
    session = db_factory()
    try:
        service = HookService(session)

        for id_ in ids:
            entity = await service.get_hook_entity(id_)
            if entity and entity.get_is_retryable():
                await _attempt_invoke_hook_entity_and_commit(
                    entity, session, retry_service, hook_config
                )
    finally:
        await session.close()


async def _attempt_invoke_hook_entity_and_commit(
    entity: HookLogEntity,
    session: AsyncSession,
    retry_service: HookRetryService,
    config: HookConfig,
) -> Any:
    """Attempt to send the hook and remove it."""
    try:
        await attempt_invoke_hook_entity(entity, retry_service, config)
    except Exception:
        # ignore errors, they were already handled
        await session.commit()
    else:
        await session.delete(entity)
        await session.commit()


async def attempt_invoke_hook_entity(
    entity: HookLogEntity,
    retry_service: HookRetryService,
    config: HookConfig,
) -> Any:
    """Attempt to invoke the hook described by a :class:`HookLogEntity`.

    If an exception occurs, the entity will be scheduled to be retried and the
    exception will be re-raised.

    Args:
        entity: The :class:`HookLogEntity`.
        retry_service: The :class:`HookRetryService`.
        config: The :class:`HookConfig`.
    """
    try:
        result = await invoke_hook_entity(entity, config)
    except Exception:
        retry_at = entity.update_attempts()
        if retry_at is not None:
            retry_service.retry_hook_id_at(retry_at, entity.id)
            retry_msg = f"Will retry at {retry_at}"
        else:
            retry_msg = "Will not retry"

        logger.opt(exception=True).error(f"Hook {entity} failed. {retry_msg}.")
        raise
    else:
        logger.debug(f"Called hook {entity}")
        return result


async def invoke_hook_entity(entity: HookLogEntity, config: HookConfig) -> Any:
    """Invoke the hook described by a :class:`HookLogEntity`."""
    hook_config = entity.get_config_entry()

    # verify that hooks retrieved from the db exist in the config (do not allow
    # running arbitrary code from a db column)
    if not config.hook_config_exists(hook_config.on, hook_config.hook):
        raise ValueError(f"Hook does not exist in config: {hook_config}")

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
