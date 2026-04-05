# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for user_setting service layer."""

from unittest.mock import AsyncMock

import pytest
from nmtfast.cache.v1.base import AppCacheBase

from app.layers.repository.v1.user_settings import UserSettingRepository
from app.layers.service.v1.user_settings import UserSettingService
from app.schemas.dto.v1.user_settings import UserSettingCreate, UserSettingRead


@pytest.fixture
def mock_user_setting_repo():
    """
    Fixture to provide a mock UserSettingRepository.
    """
    return AsyncMock(spec=UserSettingRepository)


@pytest.fixture
def user_setting_service(
    mock_user_setting_repo,
    mock_allow_acls,
    mock_settings,
    mock_cache=AsyncMock(spec=AppCacheBase),
):
    """
    Fixture to provide a UserSettingService instance.
    """
    return UserSettingService(
        mock_user_setting_repo, mock_allow_acls, mock_settings, mock_cache
    )


@pytest.mark.asyncio
async def test_user_setting_create(user_setting_service, mock_user_setting_repo):
    """
    Test creating a user_setting through the service layer.
    """
    expected = UserSettingRead(id="us-1", name="setting-1", value="val-1")
    mock_user_setting_repo.user_setting_create.return_value = expected

    input_data = UserSettingCreate(name="setting-1", value="val-1")
    result = await user_setting_service.user_setting_create(input_data)

    assert result.id == "us-1"
    assert result.name == "setting-1"
    mock_user_setting_repo.user_setting_create.assert_awaited_once_with(input_data)


@pytest.mark.asyncio
async def test_user_setting_get_by_id(user_setting_service, mock_user_setting_repo):
    """
    Test retrieving a user_setting by ID through the service layer.
    """
    expected = UserSettingRead(id="us-1", name="setting-1", value="val-1")
    mock_user_setting_repo.get_by_id.return_value = expected

    result = await user_setting_service.user_setting_get_by_id("us-1")

    assert result.id == "us-1"
    mock_user_setting_repo.get_by_id.assert_awaited_once_with("us-1")
