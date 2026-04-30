# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""
Business logic for user settings in the Web UI.

Provides get and update operations for per-user preferences
(display name, timezone) backed by the UserSetting MongoDB repository.
"""

import logging
from dataclasses import dataclass

from app.layers.repository.v1.user_settings import UserSettingRepository

logger = logging.getLogger(__name__)


@dataclass
class UserPreferences:
    """
    Aggregated user preferences returned to the template layer.

    Attributes:
        display_name: The user's chosen display name.
        timezone: The user's chosen timezone (IANA format).
        page_size: The user's preferred number of items per page.
    """

    display_name: str = ""
    timezone: str = ""
    page_size: int = 10


class WebUIUserSettingsService:
    """
    Service layer for Web UI user settings operations.

    Args:
        user_setting_repository: The repository for user_setting data
            operations.
    """

    def __init__(
        self,
        user_setting_repository: UserSettingRepository,
    ) -> None:
        self.repo: UserSettingRepository = user_setting_repository

    async def get_preferences(self, user_id: str) -> UserPreferences:
        """
        Retrieve the current user preferences.

        Args:
            user_id: The ID of the user whose preferences to fetch.

        Returns:
            UserPreferences: The aggregated preferences, with empty
                strings for any missing settings.
        """
        display_name_setting = await self.repo.get_by_user_and_name(
            user_id, "display_name"
        )
        timezone_setting = await self.repo.get_by_user_and_name(user_id, "timezone")
        page_size_setting = await self.repo.get_by_user_and_name(user_id, "page_size")

        page_size = 10
        if page_size_setting:
            try:
                page_size = int(page_size_setting.value)
            except (ValueError, TypeError):
                page_size = 10

        return UserPreferences(
            display_name=(display_name_setting.value if display_name_setting else ""),
            timezone=(timezone_setting.value if timezone_setting else ""),
            page_size=page_size,
        )

    async def update_preferences(
        self,
        user_id: str,
        display_name: str,
        timezone: str,
        page_size: int = 10,
    ) -> UserPreferences:
        """
        Create or update the user's display name, timezone, and page size settings.

        Args:
            user_id: The ID of the user whose preferences to update.
            display_name: The new display name value.
            timezone: The new timezone value (IANA format).
            page_size: The preferred number of items per page.

        Returns:
            UserPreferences: The updated preferences.
        """
        await self.repo.upsert_by_user_and_name(user_id, "display_name", display_name)
        await self.repo.upsert_by_user_and_name(user_id, "timezone", timezone)
        await self.repo.upsert_by_user_and_name(user_id, "page_size", str(page_size))

        logger.info(
            f"Updated preferences for user {user_id}: "
            f"display_name={display_name}, timezone={timezone}, "
            f"page_size={page_size}"
        )

        return UserPreferences(
            display_name=display_name,
            timezone=timezone,
            page_size=page_size,
        )
