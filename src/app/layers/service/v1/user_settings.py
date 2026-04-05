# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Business logic for user_setting resources."""

import logging

from nmtfast.auth.v1.acl import check_acl
from nmtfast.cache.v1.base import AppCacheBase

from app.core.v1.settings import AppSettings
from app.layers.repository.v1.user_settings import UserSettingRepository
from app.schemas.dto.v1.user_settings import (
    UserSettingCreate,
    UserSettingRead,
)

logger = logging.getLogger(__name__)


class UserSettingService:
    """
    Service layer for user_setting business logic.

    Args:
        user_setting_repository: The repository for user_setting data operations.
        acls: List of ACLs associated with authenticated client/apikey.
        settings: The application's AppSettings object.
        cache: An implementation of AppCacheBase, for getting/setting cached data.
    """

    def __init__(
        self,
        user_setting_repository: UserSettingRepository,
        acls: list,
        settings: AppSettings,
        cache: AppCacheBase,
    ) -> None:
        self.user_setting_repository: UserSettingRepository = user_setting_repository
        self.acls = acls
        self.settings = settings
        self.cache = cache

    async def _is_authz(self, acls: list, permission: str) -> None:
        """
        Check if the ACLs allow access to the given resource.

        Args:
            acls: List of ACLs associated with this client
            permission: Required in order to complete the requested operation.
        """
        # NOTE: by default, check_acl now raises AuthorizationError on failure
        await check_acl("user_settings", acls, permission)

    async def user_setting_create(
        self, input_user_setting: UserSettingCreate
    ) -> UserSettingRead:
        """
        Create a new user_setting.

        Args:
            input_user_setting: The user_setting data provided by the client.

        Returns:
            UserSettingRead: The newly created user_setting as a Pydantic model.
        """
        await self._is_authz(self.acls, "create")
        db_user_setting = await self.user_setting_repository.user_setting_create(
            input_user_setting
        )

        return UserSettingRead.model_validate(db_user_setting)

    async def user_setting_get_by_id(self, user_setting_id: str) -> UserSettingRead:
        """
        Retrieve a user_setting by its ID.

        Args:
            user_setting_id: The ID of the user_setting to retrieve.

        Returns:
            UserSettingRead: The retrieved user_setting.
        """
        await self._is_authz(self.acls, "read")
        db_user_setting = await self.user_setting_repository.get_by_id(user_setting_id)

        return UserSettingRead.model_validate(db_user_setting)
