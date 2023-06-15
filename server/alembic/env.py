"""Alembic environment file."""
import asyncio
from pathlib import Path

from alembic import context
from oes.registration.entities.base import metadata as target_metadata
from oes.registration.log import setup_logging
from ruamel.yaml import YAML
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

setup_logging()

yaml = YAML(typ="safe")
config = context.config


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_db_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    url = get_db_url()
    engine = create_async_engine(url, poolclass=pool.NullPool)
    asyncio.run(run_async_migrations(engine))


async def run_async_migrations(engine):
    """Async migration runner."""
    async with engine.connect() as connection:
        await connection.run_sync(run_migrations)
    await engine.dispose()


def run_migrations(connection):
    """Run migrations synchronously."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def get_db_url():
    """Get the DB url from the config file."""
    config_base_dir = Path(config.config_file_name).parent
    config_path_str = config.get_section_option("oes.registration", "config_file")

    config_path = config_base_dir / Path(config_path_str)

    doc = yaml.load(config_path)
    return doc["database"]["url"]


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
