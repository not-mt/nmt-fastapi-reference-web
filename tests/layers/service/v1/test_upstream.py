# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for widget API service layer."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from nmtfast.auth.v1.exceptions import AuthorizationError
from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.errors.v1.exceptions import UpstreamApiException
from nmtfast.repositories.widgets.v1.api import WidgetApiRepository
from nmtfast.repositories.widgets.v1.exceptions import WidgetApiException
from nmtfast.repositories.widgets.v1.schemas import (
    WidgetCreate,
    WidgetRead,
    WidgetZap,
    WidgetZapTask,
)

from app.core.v1.settings import AppSettings
from app.layers.service.v1.upstream import WidgetApiService


@pytest.fixture
def mock_settings():
    """
    Fixture to provide a mock AppSettings.
    """
    return AsyncMock(spec=AppSettings)


@pytest.fixture
def mock_api_repository():
    """
    Fixture to provide a mock API repository.
    """
    return AsyncMock(spec=WidgetApiRepository)


@pytest.fixture
def mock_cache():
    """
    Fixture to provide a mock app_cache.
    """
    return AsyncMock(spec=AppCacheBase)


@pytest.fixture
def mock_widget_create():
    """
    Fixture to provide a mock WidgetCreate model.
    """
    return WidgetCreate(name="Test Widget")


@pytest.fixture
def mock_widget_read():
    """
    Fixture to provide a mock WidgetRead model.
    """
    return WidgetRead(id=1, name="Test Widget")


@pytest.fixture
def mock_widget_zap():
    """
    Fixture to provide a mock WidgetZap model.
    """
    return WidgetZap(duration=5)


@pytest.fixture
def mock_widget_zap_task():
    """
    Fixture to provide a mock WidgetZapTask model.
    """
    return WidgetZapTask(uuid="test-uuid", id=1, state="PENDING", duration=5, runtime=0)


@pytest.fixture
def mock_error_response():
    """
    Fixture for creating a mock error response.
    """
    response = MagicMock(spec=httpx.Response)
    response.status_code = 500
    response.text = "Internal Server Error"
    response.headers = {"x-request-id": "req-123"}

    return response


@pytest.mark.asyncio
async def test_widget_create_success(
    mock_api_repository, mock_allow_acls, mock_settings, mock_cache, mock_widget_create
):
    """
    Test successful widget creation.
    """
    service = WidgetApiService(
        mock_api_repository, mock_allow_acls, mock_settings, mock_cache
    )

    repo_widget = WidgetRead(id=1, name="Test Widget")
    mock_api_repository.widget_create = AsyncMock(return_value=repo_widget)

    result = await service.widget_create(mock_widget_create)

    mock_api_repository.widget_create.assert_awaited_once()
    assert isinstance(result, WidgetRead)
    assert result.id == 1
    assert result.name == "Test Widget"


@pytest.mark.asyncio
async def test_widget_create_authorization_error(
    mock_api_repository, mock_deny_acls, mock_settings, mock_cache, mock_widget_create
):
    """
    Test authorization error during widget creation.
    """
    service = WidgetApiService(
        mock_api_repository, mock_deny_acls, mock_settings, mock_cache
    )

    with pytest.raises(AuthorizationError):
        await service.widget_create(mock_widget_create)


@pytest.mark.asyncio
async def test_widget_create_api_error(
    mock_api_repository,
    mock_allow_acls,
    mock_settings,
    mock_cache,
    mock_widget_create,
    mock_error_response,
):
    """
    Test upstream API error during widget creation.
    """
    service = WidgetApiService(
        mock_api_repository, mock_allow_acls, mock_settings, mock_cache
    )

    mock_api_repository.widget_create = AsyncMock(
        side_effect=WidgetApiException(mock_error_response)
    )

    with pytest.raises(UpstreamApiException) as exc_info:
        await service.widget_create(mock_widget_create)

    assert exc_info.value.status_code == 500
    assert exc_info.value.message == "Internal Server Error"
    assert exc_info.value.req_id == "req-123"


@pytest.mark.asyncio
async def test_widget_get_by_id_success(
    mock_api_repository, mock_allow_acls, mock_settings, mock_cache
):
    """
    Test successful widget retrieval by ID.
    """
    service = WidgetApiService(
        mock_api_repository, mock_allow_acls, mock_settings, mock_cache
    )

    repo_widget = WidgetRead(id=1, name="Test Widget")
    mock_api_repository.get_by_id = AsyncMock(return_value=repo_widget)

    result = await service.widget_get_by_id(1)

    mock_api_repository.get_by_id.assert_awaited_once_with(1)
    assert isinstance(result, WidgetRead)
    assert result.id == 1


@pytest.mark.asyncio
async def test_widget_get_by_id_api_error(
    mock_api_repository, mock_allow_acls, mock_settings, mock_cache, mock_error_response
):
    """
    Test upstream API error during widget retrieval.
    """
    service = WidgetApiService(
        mock_api_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_api_repository.get_by_id = AsyncMock(
        side_effect=WidgetApiException(mock_error_response)
    )

    # expect the service to convert to UpstreamApiException
    with pytest.raises(UpstreamApiException) as exc_info:
        await service.widget_get_by_id(1)

    # verify the converted exception properties
    assert exc_info.value.status_code == 500
    assert exc_info.value.message == "Internal Server Error"
    assert exc_info.value.req_id == "req-123"
    assert exc_info.value.caller_status_code == 502  # Since it's a 500 error


@pytest.mark.asyncio
async def test_widget_zap_success(
    mock_api_repository, mock_allow_acls, mock_settings, mock_cache, mock_widget_zap
):
    """
    Test successful widget zap operation.
    """
    service = WidgetApiService(
        mock_api_repository, mock_allow_acls, mock_settings, mock_cache
    )

    repo_task = WidgetZapTask(
        uuid="test-uuid", id=1, state="PENDING", duration=5, runtime=0
    )
    mock_api_repository.widget_zap = AsyncMock(return_value=repo_task)

    result = await service.widget_zap(1, mock_widget_zap)

    mock_api_repository.widget_zap.assert_awaited_once_with(1, mock_widget_zap)
    assert isinstance(result, WidgetZapTask)
    assert result.uuid == "test-uuid"


@pytest.mark.asyncio
async def test_widget_zap_api_error(
    mock_api_repository,
    mock_allow_acls,
    mock_settings,
    mock_cache,
    mock_widget_zap,
    mock_error_response,
):
    """
    Test upstream API error during widget zap.
    """
    service = WidgetApiService(
        mock_api_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_api_repository.widget_zap = AsyncMock(
        side_effect=WidgetApiException(mock_error_response)
    )

    # service should convert to UpstreamApiException
    with pytest.raises(UpstreamApiException) as exc_info:
        await service.widget_zap(1, mock_widget_zap)

    # verify exception properties
    assert exc_info.value.status_code == 500
    assert exc_info.value.message == "Internal Server Error"
    assert exc_info.value.req_id == "req-123"
    assert exc_info.value.caller_status_code == 502  # 500 maps to 502


@pytest.mark.asyncio
async def test_widget_zap_by_uuid_success(
    mock_api_repository, mock_allow_acls, mock_settings, mock_cache
):
    """
    Test successful widget zap task retrieval.
    """
    service = WidgetApiService(
        mock_api_repository, mock_allow_acls, mock_settings, mock_cache
    )

    repo_task = WidgetZapTask(
        uuid="test-uuid",
        id=1,
        state="COMPLETE",
        duration=5,
        runtime=5,
    )
    mock_api_repository.widget_zap_by_uuid = AsyncMock(return_value=repo_task)

    result = await service.widget_zap_by_uuid(1, "test-uuid")

    mock_api_repository.widget_zap_by_uuid.assert_awaited_once_with(1, "test-uuid")
    assert isinstance(result, WidgetZapTask)
    assert result.state == "COMPLETE"


@pytest.mark.asyncio
async def test_widget_zap_by_uuid_api_error(
    mock_api_repository, mock_allow_acls, mock_settings, mock_cache, mock_error_response
):
    """Test upstream API error during zap task retrieval."""
    service = WidgetApiService(
        mock_api_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_api_repository.widget_zap_by_uuid = AsyncMock(
        side_effect=WidgetApiException(mock_error_response)
    )

    # service should convert to UpstreamApiException
    with pytest.raises(UpstreamApiException) as exc_info:
        await service.widget_zap_by_uuid(1, "test-uuid")

    # verify all exception properties
    assert exc_info.value.status_code == 500
    assert exc_info.value.message == "Internal Server Error"
    assert exc_info.value.req_id == "req-123"
    assert exc_info.value.caller_status_code == 502  # 500 maps to 502

    # verify repository was called correctly
    mock_api_repository.widget_zap_by_uuid.assert_awaited_once_with(1, "test-uuid")
