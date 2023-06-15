import asyncio
import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, create_autospec, patch

import pytest
import pytest_asyncio
from loguru._asyncio_loop import get_running_loop
from oes.registration.hook.models import HookConfig
from oes.registration.hook.service import CommitCallbackService, HookRetryService
from oes.registration.util import get_now
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session


@pytest.fixture
def db_factory():
    return create_autospec(async_sessionmaker)


@pytest_asyncio.fixture
async def commit_callback_service():
    loop = asyncio.get_running_loop()
    return CommitCallbackService(loop)


@pytest.mark.asyncio
async def test_commit_callback_service(
    db_factory: async_sessionmaker, commit_callback_service: CommitCallbackService
):
    callback1 = AsyncMock()
    callback2 = AsyncMock()
    callback_other = AsyncMock()

    async_session = db_factory()
    other_session = create_autospec(AsyncSession)

    sync_session = create_autospec(Session)
    sync_other_session = create_autospec(Session)

    async_session.sync_session = sync_session
    other_session.sync_session = sync_other_session

    commit_callback_service.add_callback(async_session, callback1, "test1")
    commit_callback_service.add_callback(async_session, callback2, arg="test2")
    commit_callback_service.add_callback(other_session, callback_other)

    loop = get_running_loop()
    fut = await loop.run_in_executor(
        None, commit_callback_service._on_commit, sync_session
    )
    await loop.run_in_executor(None, fut.exception)

    callback1.assert_called_once_with("test1")
    callback2.assert_called_once_with(arg="test2")
    callback_other.assert_not_called()


@pytest.mark.asyncio
async def test_commit_callback_service_rollback(
    db_factory: async_sessionmaker, commit_callback_service: CommitCallbackService
):
    callback = AsyncMock()

    async_session = db_factory()
    sync_session = create_autospec(Session)
    async_session.sync_session = sync_session
    commit_callback_service.add_callback(async_session, callback)

    loop = get_running_loop()
    fut = await loop.run_in_executor(
        None, commit_callback_service._on_rollback, sync_session
    )
    await loop.run_in_executor(None, fut.exception)
    callback.assert_not_called()


@pytest.mark.asyncio
@patch("oes.registration.hook.service.get_now")
@patch("oes.registration.hook.service.asyncio")
@patch("oes.registration.hook.service.attempt_invoke_hooks")
async def test_retry_hook_id_at(mock_attempt_invoke_hooks, mock_asyncio, mock_get_now):
    loop = get_running_loop()
    session_factory = create_autospec(async_sessionmaker)
    config = create_autospec(HookConfig)

    cur_time = get_now()
    later = get_now() + timedelta(seconds=3)
    diff = (later - cur_time).total_seconds()

    mock_get_now.side_effect = lambda: cur_time

    async def _sleep(t):
        nonlocal cur_time
        cur_time = cur_time + timedelta(seconds=t)

    mock_asyncio.sleep = AsyncMock(side_effect=_sleep)
    retry_service = HookRetryService(loop, config, session_factory)

    id_ = uuid.uuid4()
    task = retry_service.retry_hook_id_at(later, id_)
    await task

    mock_asyncio.sleep.assert_called_with(diff)
    mock_attempt_invoke_hooks.assert_called_with(
        [id_], retry_service, session_factory, config
    )


@pytest.mark.asyncio
@patch("oes.registration.hook.service.attempt_invoke_hooks")
async def test_retry_service_cancel(_mock_attempt_invoke_hooks):
    loop = get_running_loop()
    session_factory = create_autospec(async_sessionmaker)
    config = create_autospec(HookConfig)
    retry_service = HookRetryService(loop, config, session_factory)

    later = get_now() + timedelta(seconds=10)

    id_ = uuid.uuid4()
    task = retry_service.retry_hook_id_at(later, id_)

    await retry_service.close()
    assert task.cancelled()
