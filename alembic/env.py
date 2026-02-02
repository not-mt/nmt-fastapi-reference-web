import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import AsyncConnection, async_engine_from_config

from app.core.v1.sqlalchemy import Base
from app.core.v1.settings import get_app_settings

# Alembic Config object
config = context.config

# Configure logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Load the database URL from settings
settings = get_app_settings()
if not settings.sqlalchemy.url:
    raise ValueError("sqlalchemy.url not found in settings!")

# Override sqlalchemy.url with the async database URL
config.set_main_option("sqlalchemy.url", settings.sqlalchemy.url)

# Target metadata for 'autogenerate' support
target_metadata = Base.metadata


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode with async support."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=None,
        future=True,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(run_migrations)

    await connectable.dispose()


def run_migrations(connection: AsyncConnection) -> None:
    """Run migrations within a given connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode without a live connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# Entry point for migrations
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
