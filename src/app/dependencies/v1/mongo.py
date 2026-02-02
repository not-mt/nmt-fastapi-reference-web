# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Dependencies related to MongoDB."""

from fastapi import Depends
from pymongo.asynchronous.database import AsyncDatabase as AsyncMongoDatabase

from app.core.v1.mongo import async_client
from app.core.v1.settings import AppSettings, get_app_settings


async def get_mongo_db(
    settings: AppSettings = Depends(get_app_settings),
) -> AsyncMongoDatabase:
    """
    Provide an async MongoDB database for FastAPI endpoints.

    This returns a async Database from a client object that was created
    in app.core.v1.mongo.

    Args:
        settings: The application settings.

    Returns:
        AsyncMongoDatabase: An async MongoDB client.
    """
    assert async_client is not None, "async_client is not initialized"

    return async_client[settings.mongo.db]
