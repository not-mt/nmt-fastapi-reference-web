# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""MongoDB client setup."""

import logging
from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar

from pymongo import AsyncMongoClient, MongoClient

from app.core.v1.settings import get_app_settings

settings = get_app_settings()
async_client: AsyncMongoClient | None = None
sync_client: MongoClient | None = None

if settings.mongo.url:
    async_client = AsyncMongoClient(settings.mongo.url)
    sync_client = MongoClient(settings.mongo.url)

T = TypeVar("T")

logger = logging.getLogger(__name__)


def with_huey_mongo_session(
    func: Callable[..., Coroutine[Any, Any, T]],
) -> Callable[..., Coroutine[Any, Any, T]]:
    """
    Decorator to inject an async MongoDB database instance into Huey tasks.

    This creates a new client and database handle per task, injecting it into
    the decorated async function as 'mongo_client' and ensures proper cleanup.

    Args:
        func: The asynchronous function to be decorated. It must accept
              a `mongo_client` keyword argument.

    Returns:
        Callable[..., Coroutine[Any, Any, T]]: A new asynchronous function that
            wraps the original, managing the database connection lifecycle.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        db_name = settings.mongo.db
        huey_async_client: AsyncMongoClient = AsyncMongoClient(settings.mongo.url)
        mongo_client = huey_async_client[db_name]

        try:
            logger.debug(f"Running: {func.__qualname__} with MongoDB: {db_name}")
            kwargs["mongo_client"] = mongo_client
            result = await func(*args, **kwargs)
            return result
        except Exception as exc:
            logger.critical(
                f"Error in {func.__qualname__} using MongoDB: {exc}",
                exc_info=True,
            )
            raise
        finally:
            logger.debug(f"Cleaned up MongoDB client for: {func.__qualname__}")
            await huey_async_client.close()

    return wrapper
