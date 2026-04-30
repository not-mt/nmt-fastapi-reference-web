# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for WebUIUserSettingsService."""

from unittest.mock import AsyncMock

import pytest

from app.layers.repository.v1.user_settings import UserSettingRepository
from app.layers.service.v1.web_user_settings import (
    UserPreferences,
    WebUIUserSettingsService,
)
from app.schemas.dto.v1.user_settings import UserSettingRead


@pytest.fixture
def mock_repo():
    """
    Fixture providing a mock UserSettingRepository.
    """
    return AsyncMock(spec=UserSettingRepository)


@pytest.fixture
def service(mock_repo):
    """
    Fixture providing a WebUIUserSettingsService with a mocked repository.
    """
    return WebUIUserSettingsService(mock_repo)


@pytest.mark.asyncio
async def test_get_preferences(service, mock_repo):
    """
    Test get_preferences aggregates settings from repository.
    """
    mock_repo.get_by_user_and_name = AsyncMock(
        side_effect=[
            UserSettingRead(id="s1", user_id="u1", name="display_name", value="Alice"),
            UserSettingRead(id="s2", user_id="u1", name="timezone", value="US/Eastern"),
            UserSettingRead(id="s3", user_id="u1", name="page_size", value="25"),
        ]
    )
    result = await service.get_preferences("u1")

    assert result.display_name == "Alice"
    assert result.timezone == "US/Eastern"
    assert result.page_size == 25


@pytest.mark.asyncio
async def test_get_preferences_missing_settings(service, mock_repo):
    """
    Test get_preferences returns defaults when settings are missing.
    """
    mock_repo.get_by_user_and_name = AsyncMock(return_value=None)
    result = await service.get_preferences("u1")

    assert result.display_name == ""
    assert result.timezone == ""
    assert result.page_size == 10


@pytest.mark.asyncio
async def test_get_preferences_invalid_page_size(service, mock_repo):
    """
    Test get_preferences handles invalid page_size gracefully.
    """
    mock_repo.get_by_user_and_name = AsyncMock(
        side_effect=[
            None,
            None,
            UserSettingRead(
                id="s3", user_id="u1", name="page_size", value="not_a_number"
            ),
        ]
    )
    result = await service.get_preferences("u1")
    assert result.page_size == 10


@pytest.mark.asyncio
async def test_update_preferences(service, mock_repo):
    """
    Test update_preferences upserts all three settings.
    """
    mock_repo.upsert_by_user_and_name = AsyncMock(return_value=None)
    result = await service.update_preferences("u1", "Alice", "US/Eastern", 25)

    assert isinstance(result, UserPreferences)
    assert result.display_name == "Alice"
    assert result.timezone == "US/Eastern"
    assert result.page_size == 25
    assert mock_repo.upsert_by_user_and_name.await_count == 3
