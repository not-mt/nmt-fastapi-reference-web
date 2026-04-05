# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for user_settings router layer."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies.v1.auth import authenticate_headers
from app.errors.v1.exceptions import ResourceNotFoundError
from app.layers.router.v1.user_settings import get_user_setting_service
from app.layers.service.v1.user_settings import UserSettingService
from app.main import app
from app.schemas.dto.v1.user_settings import UserSettingRead

client = TestClient(app)


def test_get_user_setting_service_returns_service():
    """
    Test that get_user_setting_service returns a UserSettingService instance.
    """
    result = get_user_setting_service(
        db=MagicMock(), acls=[], settings=MagicMock(), cache=MagicMock()
    )
    assert isinstance(result, UserSettingService)


@pytest.fixture
def mock_user_setting_service():
    """
    Fixture to provide a mock UserSettingService.
    """
    return AsyncMock(spec=UserSettingService)


@pytest.fixture
def mock_user_setting_read():
    """
    Fixture to provide a test UserSettingRead instance.
    """
    return UserSettingRead(id="us-1", name="setting-1", value="val-1")


@pytest.mark.asyncio
async def test_user_setting_create_endpoint(
    mock_api_key,
    mock_user_setting_service,
    mock_user_setting_read,
):
    """
    Test creating a user_setting via POST endpoint.
    """

    def override_service():
        return mock_user_setting_service

    def override_auth():
        return "Authenticated successfully."

    app.dependency_overrides[get_user_setting_service] = override_service
    app.dependency_overrides[authenticate_headers] = override_auth
    mock_user_setting_service.user_setting_create = AsyncMock(
        return_value=mock_user_setting_read
    )

    response = client.post(
        "/v1/user_settings/",
        headers={"X-API-Key": mock_api_key},
        json={"name": "setting-1", "value": "val-1"},
    )
    assert response.status_code == 201
    assert response.json() == mock_user_setting_read.model_dump()

    app.dependency_overrides.pop(get_user_setting_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)


@pytest.mark.asyncio
async def test_user_setting_get_by_id_endpoint(
    mock_api_key,
    mock_user_setting_service,
    mock_user_setting_read,
):
    """
    Test retrieving a user_setting via GET endpoint.
    """

    def override_service():
        return mock_user_setting_service

    def override_auth():
        return "Authenticated successfully."

    app.dependency_overrides[get_user_setting_service] = override_service
    app.dependency_overrides[authenticate_headers] = override_auth
    mock_user_setting_service.user_setting_get_by_id = AsyncMock(
        return_value=mock_user_setting_read
    )

    response = client.get(
        "/v1/user_settings/us-1",
        headers={"X-API-Key": mock_api_key},
    )
    assert response.status_code == 200
    assert response.json() == mock_user_setting_read.model_dump()

    app.dependency_overrides.pop(get_user_setting_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)


@pytest.mark.asyncio
async def test_user_setting_get_by_id_not_found(
    mock_api_key,
    mock_user_setting_service,
):
    """
    Test that GET endpoint returns 404 when user_setting is not found.
    """

    def override_service():
        return mock_user_setting_service

    def override_auth():
        return "Authenticated successfully."

    app.dependency_overrides[get_user_setting_service] = override_service
    app.dependency_overrides[authenticate_headers] = override_auth
    mock_user_setting_service.user_setting_get_by_id = AsyncMock(
        side_effect=ResourceNotFoundError(
            resource_id="us-999", resource_name="UserSetting"
        )
    )

    response = client.get(
        "/v1/user_settings/us-999",
        headers={"X-API-Key": mock_api_key},
    )
    assert response.status_code == 404

    app.dependency_overrides.pop(get_user_setting_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)
