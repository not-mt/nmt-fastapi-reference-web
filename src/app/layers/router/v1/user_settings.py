# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""This module defines API endpoints for managing user_settings."""

import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, status
from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.settings.v1.schemas import SectionACL
from pymongo.asynchronous.database import AsyncDatabase as AsyncMongoDatabase

from app.core.v1.settings import AppSettings
from app.dependencies.v1.auth import authenticate_headers, get_acls
from app.dependencies.v1.cache import get_cache
from app.dependencies.v1.mongo import get_mongo_db
from app.dependencies.v1.settings import get_settings
from app.layers.repository.v1.user_settings import UserSettingRepository
from app.layers.service.v1.user_settings import UserSettingService
from app.schemas.dto.v1.user_settings import (
    UserSettingCreate,
    UserSettingRead,
)

logger = logging.getLogger(__name__)
user_settings_router = APIRouter(
    prefix="/v1/user_settings",
    tags=["UserSetting Operations (MongoDB)"],
    dependencies=[Depends(authenticate_headers)],
)


def get_user_setting_service(
    db: AsyncMongoDatabase = Depends(get_mongo_db),
    acls: list[SectionACL] = Depends(get_acls),
    settings: AppSettings = Depends(get_settings),
    cache: AppCacheBase = Depends(get_cache),
) -> UserSettingService:
    """
    Dependency function to provide a UserSettingService instance.

    Args:
        db: The asynchronous MongoDB database.
        acls: List of ACLs associated with authenticated client/apikey.
        settings: The application's AppSettings object.
        cache: An implementation of AppCacheBase, for getting/setting cache data.

    Returns:
        UserSettingService: An instance of the user_setting service.
    """
    user_setting_repository = UserSettingRepository(db)

    return UserSettingService(user_setting_repository, acls, settings, cache)


@user_settings_router.post(
    path="",
    response_model=UserSettingRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user_setting",
    description="Create a user_setting",  # Override the docstring in Swagger UI
)
async def user_setting_create(
    user_setting: Annotated[
        UserSettingCreate,
        Body(
            openapi_examples={
                "normal": {
                    "summary": "Create a user_setting",
                    "description": (
                        "A **normal** user_setting that is created successfully."
                    ),
                    "value": {
                        "name": "user_setting-123",
                        "value": "value-abc",
                    },
                },
            },
        ),
    ],
    user_setting_service: UserSettingService = Depends(get_user_setting_service),
) -> UserSettingRead:
    """
    Create a new user_setting.

    Args:
        user_setting: The user_setting data provided in the request.
        user_setting_service: The user_setting service instance.

    Returns:
        UserSettingRead: The created user_setting data.
    """
    logger.info(f"Attempting to create a user_setting: {user_setting}")
    return await user_setting_service.user_setting_create(user_setting)


@user_settings_router.get(
    "/{user_setting_id}",
    response_model=UserSettingRead,
    status_code=status.HTTP_200_OK,
    summary="View (read) a user_setting",
    description="View (read) a user_setting",  # Override the docstring in Swagger UI
)
async def user_setting_get_by_id(
    user_setting_id: Annotated[
        str,
        Path(description="The ID of the user_setting to retrieve."),
    ],
    user_setting_service: UserSettingService = Depends(get_user_setting_service),
) -> UserSettingRead:
    """
    Retrieve a user_setting by its ID.

    Args:
        user_setting_id: The ID of the user_setting to retrieve.
        user_setting_service: The user_setting service instance.

    Returns:
        UserSettingRead: The retrieved user_setting data.
    """
    logger.info(f"Attempting to find user_setting {user_setting_id}")
    return await user_setting_service.user_setting_get_by_id(user_setting_id)
