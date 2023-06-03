import os
from pathlib import Path

import pytest
import pytest_asyncio
from oes.registration.config import load_event_config
from oes.registration.database import DBConfig
from oes.registration.models.event import EventConfig


@pytest_asyncio.fixture
async def db_config():
    url = os.getenv("TEST_DB_URL", None)
    if url is None:
        pytest.skip("Set the TEST_DB_URL env var to test with a database")

    config = DBConfig.create(url)
    await config.create_tables()
    yield config
    await config.drop_tables()
    await config.close()


@pytest_asyncio.fixture
async def db(db_config: DBConfig):
    session = db_config.session_factory()
    yield session
    await session.close()


@pytest.fixture
def example_events() -> EventConfig:
    return load_event_config(Path("tests/test_data/events.yml"))
