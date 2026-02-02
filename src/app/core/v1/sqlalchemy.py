# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""SQLAlchemy engine and session setup."""

import logging
import ssl
from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.v1.settings import get_app_settings

logger = logging.getLogger(__name__)
settings = get_app_settings()
Base = declarative_base()  # needed for Alembic migrations

# NOTE: asynchronous SQLAlchemy engine and session should be used with
#   dependency injection for normal API calls

# default connection arguments; we can modify depending on config settings
connect_args = settings.sqlalchemy.connect_args

# create an engine by default, and overwrite it with SSL if necessary
async_engine = create_async_engine(
    settings.sqlalchemy.url,
    echo=settings.sqlalchemy.echo,
    connect_args=connect_args,
    echo_pool=settings.sqlalchemy.echo_pool,
    max_overflow=settings.sqlalchemy.max_overflow,
    pool_pre_ping=settings.sqlalchemy.pool_pre_ping,
    pool_size=settings.sqlalchemy.pool_size,
    pool_timeout=settings.sqlalchemy.pool_timeout,
    pool_recycle=settings.sqlalchemy.pool_recycle,
)
# NOTE: the Huey SQLAlchemy engine and session should ONLY BE USED for
#   background tasks that are scheduled and executed by Huey (duh)
huey_engine = create_async_engine(
    url=settings.sqlalchemy.url,
    echo=settings.sqlalchemy.echo,
    connect_args=connect_args,
)

if settings.sqlalchemy.ssl_mode == "default":
    # NOTE: asyncpg and aiomysql require using an actual SSLContext, and
    #   not strings
    ssl_context = ssl.create_default_context()
    connect_args["ssl"] = ssl_context

    async_engine = create_async_engine(
        url=settings.sqlalchemy.url,
        echo=settings.sqlalchemy.echo,
        connect_args=connect_args,
        echo_pool=settings.sqlalchemy.echo_pool,
        max_overflow=settings.sqlalchemy.max_overflow,
        pool_pre_ping=settings.sqlalchemy.pool_pre_ping,
        pool_size=settings.sqlalchemy.pool_size,
        pool_timeout=settings.sqlalchemy.pool_timeout,
        pool_recycle=settings.sqlalchemy.pool_recycle,
    )

    # NOTE: the Huey SQLAlchemy engine and session should ONLY BE USED for
    #   background tasks that are scheduled and executed by Huey (duh)
    huey_engine = create_async_engine(
        url=settings.sqlalchemy.url,
        echo=settings.sqlalchemy.echo,
        connect_args=connect_args,
    )

async_session = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)
huey_session = async_sessionmaker(
    bind=huey_engine, class_=AsyncSession, expire_on_commit=False
)

# Convert async URL to sync
async_url = settings.sqlalchemy.url
sync_url = (
    async_url.replace("sqlite+aiosqlite://", "sqlite://")
    .replace("mysql+aiomysql://", "mysql+pymysql://")
    .replace("postgresql+asyncpg://", "postgresql+psycopg2://")
)

# NOTE: synchronous SQLAlchemy engine and session should ONLY BE USED for
#   Alembic (it may be refactored later)
sync_engine = create_engine(
    url=sync_url,
    echo=settings.sqlalchemy.echo,
    connect_args=connect_args,
    echo_pool=settings.sqlalchemy.echo_pool,
    max_overflow=settings.sqlalchemy.max_overflow,
    pool_pre_ping=settings.sqlalchemy.pool_pre_ping,
    pool_size=settings.sqlalchemy.pool_size,
    pool_timeout=settings.sqlalchemy.pool_timeout,
    pool_recycle=settings.sqlalchemy.pool_recycle,
)
sync_session = sessionmaker(bind=sync_engine)

T = TypeVar("T")  # preserves the return type of the original coroutine


def with_huey_db_session(
    func: Callable[..., Coroutine[Any, Any, T]],
) -> Callable[..., Coroutine[Any, Any, T]]:
    """
    Specialized session decorator for Huey tasks.

    This is designed to creates a new session per task and ensure complete cleanup
    and breakdown of DB sessions for async tasks.

    Args:
        func: The asynchronous function to be wrapped. This function is expected
            to accept a 'db_session' keyword argument.

    Returns:
        Callable[..., Coroutine[Any, Any, T]]: A new asynchronous function that
            wraps the original, managing the database session lifecycle.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        async with huey_session() as session:
            try:
                kwargs["db_session"] = session
                logger.debug(f"Running: {func.__qualname__}")
                result = await func(*args, **kwargs)
                await session.commit()
                return result
            except Exception as exc:
                logger.critical(
                    f"Error in {func.__qualname__}, rolling back session: {exc}",
                    exc_info=True,
                )
                await session.rollback()
                raise
            finally:
                await session.close()
                await huey_engine.dispose()  # Clean up all connection pools
                logger.debug(f"Disposed DB engine after: {func.__qualname__}")

    return wrapper
