# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Repository layer for UserSetting resources."""

import logging
from typing import Any
from uuid import uuid4

from nmtfast.retry.v1.tenacity import tenacity_retry_log
from pymongo import ReturnDocument
from pymongo.asynchronous.collection import AsyncCollection as AsyncMongoCollection
from pymongo.asynchronous.database import AsyncDatabase as AsyncMongoDatabase
from tenacity import retry, stop_after_attempt, wait_fixed

from app.errors.v1.exceptions import ResourceNotFoundError
from app.schemas.dto.v1.user_settings import UserSettingCreate, UserSettingRead

logger = logging.getLogger(__name__)


class UserSettingRepository:
    """
    Repository implementation for UserSetting operations.

    Args:
        db: The asynchronous MongoDB database.
    """

    def __init__(self, db: AsyncMongoDatabase) -> None:
        self.db: AsyncMongoDatabase = db
        self.collection: AsyncMongoCollection = db["user_settings"]

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def user_setting_create(
        self, user_setting: UserSettingCreate
    ) -> UserSettingRead:
        """
        Create a new user_setting and persist it to the database.

        Args:
            user_setting: The user_setting data transfer object.

        Returns:
            UserSettingRead: The newly created user_setting instance.
        """
        new_user_setting = user_setting.model_dump()
        new_user_setting["id"] = str(uuid4())

        await self.collection.insert_one(new_user_setting)
        inserted_user_setting = await self.collection.find_one(
            {"id": new_user_setting["id"]}
        )
        logger.debug(f"Inserted user_setting: {inserted_user_setting}")

        return UserSettingRead(**new_user_setting)

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def get_by_id(self, user_setting_id: str) -> UserSettingRead:
        """
        Retrieve a user_setting by its ID from the database.

        Args:
            user_setting_id: The ID of the user_setting to retrieve.

        Returns:
            UserSettingRead: The retrieved user_setting instance.

        Raises:
            ResourceNotFoundError: If the user_setting is not found.
        """
        logger.debug(f"Fetching user_setting by ID: {user_setting_id}")
        db_user_setting: dict[str, Any] | None = await self.collection.find_one(
            {"id": user_setting_id}
        )

        if db_user_setting is None:
            logger.warning(f"UserSetting with ID {user_setting_id} not found.")
            raise ResourceNotFoundError(user_setting_id, "UserSetting")

        logger.debug(f"Retrieved user_setting: {db_user_setting}")
        db_user_setting.pop("_id", None)

        return UserSettingRead(**db_user_setting)

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def update_value(
        self, user_setting_id: str, new_value: str
    ) -> UserSettingRead:
        """
        Update the value property of a user_setting.

        Args:
            user_setting_id: The ID of the user_setting to retrieve.
            new_value: The new value for the value property.

        Returns:
            UserSettingRead: The updated user_setting.

        Raises:
            ResourceNotFoundError: If the user_setting is not found.
        """
        logger.debug(
            f"Updating value for user_setting ID {user_setting_id} to {new_value}"
        )
        db_user_setting = await self.collection.find_one_and_update(
            {"id": user_setting_id},
            {"$set": {"value": new_value}},
            return_document=ReturnDocument.AFTER,
        )

        if db_user_setting is None:
            logger.warning(f"UserSetting with ID {user_setting_id} not found.")
            raise ResourceNotFoundError(user_setting_id, "UserSetting")

        logger.debug(f"UserSetting ID {user_setting_id} value updated to {new_value}")

        return UserSettingRead(**db_user_setting)
