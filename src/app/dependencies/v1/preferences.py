# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""
Dependencies for user preferences.

Provides a FastAPI dependency that resolves the authenticated user's
preferred page size from their stored settings.
"""

import logging
from typing import Optional

from fastapi import Depends
from nmtfast.auth.v1.sessions import SessionData
from pymongo.asynchronous.database import AsyncDatabase as AsyncMongoDatabase

from app.dependencies.v1.mongo import get_mongo_db
from app.dependencies.v1.session import get_current_session
from app.layers.repository.v1.user_settings import UserSettingRepository

logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE: int = 10


async def get_user_page_size(
    session: Optional[SessionData] = Depends(get_current_session),
    db: AsyncMongoDatabase = Depends(get_mongo_db),
) -> int:
    """
    Resolve the authenticated user's preferred items-per-page setting.

    Falls back to the default of 10 when the user has no stored
    preference or is not authenticated.

    Args:
        session: The current user session, if any.
        db: The asynchronous MongoDB database.

    Returns:
        int: The user's preferred page size, or the default.
    """
    if session is None:
        return DEFAULT_PAGE_SIZE

    try:
        repo = UserSettingRepository(db)
        setting = await repo.get_by_user_and_name(session.user_id, "page_size")
        if setting:
            return int(setting.value)
    except (ValueError, TypeError, Exception):
        logger.warning("Failed to fetch page_size preference, using default")

    return DEFAULT_PAGE_SIZE
