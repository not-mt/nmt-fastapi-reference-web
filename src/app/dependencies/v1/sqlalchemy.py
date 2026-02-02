# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Dependencies related to SQLAlchemy."""

import logging
from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.v1.settings import AppSettings, get_app_settings
from app.core.v1.sqlalchemy import async_session

logger = logging.getLogger(__name__)


async def get_sql_db(
    settings: AppSettings = Depends(get_app_settings),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an async sqlalchemy session for FastAPI endpoints.

    This creates an instance of async_session (using the factory that was
    imported from app.core) and using a context manager (async with) to handle
    the lifecycle of the session.

    Args:
        settings: The application settings.

    Yields:
        AsyncSession: An async SQLAlchemy session.

    Raises:
        Exception: If an error occurs during session operations, the session is rolled
            back, and the exception is re-raised.
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise  # reraise the original exception
        finally:
            await session.close()
