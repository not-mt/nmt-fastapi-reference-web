# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for UserSetting repository layer."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.errors.v1.exceptions import ResourceNotFoundError
from app.layers.repository.v1.user_settings import UserSettingRepository
from app.schemas.dto.v1.user_settings import UserSettingCreate, UserSettingRead


@pytest.fixture
def mock_collection():
    """
    Fixture to provide a mock MongoDB collection.
    """
    return MagicMock()


@pytest.fixture
def mock_mongo_db(mock_collection):
    """
    Fixture to provide a mock MongoDB database with user_settings collection.
    """
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=mock_collection)
    return db


@pytest.fixture
def user_setting_repo(mock_mongo_db):
    """
    Fixture to provide a UserSettingRepository instance.
    """
    return UserSettingRepository(mock_mongo_db)


@pytest.mark.asyncio
async def test_user_setting_create(user_setting_repo, mock_collection):
    """
    Test creating a user_setting persists and returns UserSettingRead.
    """
    mock_collection.insert_one = AsyncMock()
    mock_collection.find_one = AsyncMock(
        return_value={"id": "generated-id", "name": "setting-1", "value": "val-1"}
    )

    input_data = UserSettingCreate(name="setting-1", value="val-1")
    result = await user_setting_repo.user_setting_create(input_data)

    assert isinstance(result, UserSettingRead)
    assert result.name == "setting-1"
    assert result.value == "val-1"
    mock_collection.insert_one.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_id_success(user_setting_repo, mock_collection):
    """
    Test retrieving a user_setting by ID when it exists.
    """
    mock_collection.find_one = AsyncMock(
        return_value={
            "_id": "mongo-oid",
            "id": "us-1",
            "name": "setting-1",
            "value": "val-1",
        }
    )

    result = await user_setting_repo.get_by_id("us-1")

    assert isinstance(result, UserSettingRead)
    assert result.id == "us-1"
    assert result.name == "setting-1"
    mock_collection.find_one.assert_awaited_once_with({"id": "us-1"})


@pytest.mark.asyncio
async def test_get_by_id_not_found(user_setting_repo, mock_collection):
    """
    Test that get_by_id raises ResourceNotFoundError when not found.
    """
    mock_collection.find_one = AsyncMock(return_value=None)

    with pytest.raises(ResourceNotFoundError):
        await user_setting_repo.get_by_id("nonexistent")


@pytest.mark.asyncio
async def test_update_value_success(user_setting_repo, mock_collection):
    """
    Test updating a user_setting value when it exists.
    """
    mock_collection.find_one_and_update = AsyncMock(
        return_value={
            "id": "us-1",
            "name": "setting-1",
            "value": "new-val",
        }
    )

    result = await user_setting_repo.update_value("us-1", "new-val")

    assert isinstance(result, UserSettingRead)
    assert result.value == "new-val"
    mock_collection.find_one_and_update.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_value_not_found(user_setting_repo, mock_collection):
    """
    Test that update_value raises ResourceNotFoundError when not found.
    """
    mock_collection.find_one_and_update = AsyncMock(return_value=None)

    with pytest.raises(ResourceNotFoundError):
        await user_setting_repo.update_value("nonexistent", "new-val")


@pytest.mark.asyncio
async def test_get_by_user_and_name_found(user_setting_repo, mock_collection):
    """
    Test retrieving a user_setting by user_id and name when it exists.
    """
    mock_collection.find_one = AsyncMock(
        return_value={
            "_id": "mongo-oid",
            "id": "us-1",
            "user_id": "u1",
            "name": "page_size",
            "value": "25",
        }
    )

    result = await user_setting_repo.get_by_user_and_name("u1", "page_size")

    assert isinstance(result, UserSettingRead)
    assert result.value == "25"


@pytest.mark.asyncio
async def test_get_by_user_and_name_not_found(user_setting_repo, mock_collection):
    """
    Test get_by_user_and_name returns None when not found.
    """
    mock_collection.find_one = AsyncMock(return_value=None)

    result = await user_setting_repo.get_by_user_and_name("u1", "missing")

    assert result is None


@pytest.mark.asyncio
async def test_upsert_by_user_and_name(user_setting_repo, mock_collection):
    """
    Test upserting a user_setting by user_id and name.
    """
    mock_collection.find_one_and_update = AsyncMock(
        return_value={
            "_id": "mongo-oid",
            "id": "us-1",
            "user_id": "u1",
            "name": "timezone",
            "value": "UTC",
        }
    )

    result = await user_setting_repo.upsert_by_user_and_name("u1", "timezone", "UTC")

    assert isinstance(result, UserSettingRead)
    assert result.value == "UTC"
    mock_collection.find_one_and_update.assert_awaited_once()
