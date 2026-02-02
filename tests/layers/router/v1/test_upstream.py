# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for router layer."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient
from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.repositories.widgets.v1.api import WidgetApiRepository
from nmtfast.repositories.widgets.v1.schemas import WidgetRead, WidgetZap, WidgetZapTask
from nmtfast.settings.v1.schemas import SectionACL

from app.core.v1.settings import AppSettings
from app.errors.v1.exceptions import ResourceNotFoundError
from app.layers.router.v1.upstream import authenticate_headers, get_widget_service
from app.layers.service.v1.upstream import WidgetApiService
from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_api_client():
    """
    Fixture to provide a mock AsyncClient.
    """
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def mock_cache():
    """
    Fixture for a mock app_cache.
    """
    return AsyncMock(spec=AppCacheBase)


@pytest.fixture
def mock_widget_repository(mock_api_client):
    """
    Fixture to provide a mock WidgetRepository.
    """
    return WidgetApiRepository(mock_api_client)


@pytest.fixture
def mock_widget_service(
    mock_widget_repository,
    mock_allow_acls,
    mock_settings,
    mock_cache,
):
    """
    Fixture to provide a mock WidgetApiService.
    """
    return WidgetApiService(
        mock_widget_repository, mock_allow_acls, mock_settings, mock_cache
    )


@pytest.fixture
def mock_widget_read():
    """
    Fixture to provide a test WidgetRead instance.
    """
    return WidgetRead(id=1, name="Test Widget", height="10", mass="5", force=20)


@pytest.fixture
def mock_widget_zap_task():
    """
    Fixture to provide a test WidgetZapTask instance.
    """
    return WidgetZapTask(
        uuid="uuid-here",
        state="PENDING",
        id=1,
        duration=1,
        runtime=0,
    )


@pytest.mark.asyncio
async def test_widget_create_endpoint_success(
    mock_api_key,
    mock_widget_service,
    mock_widget_read,
):
    """
    Unit test for the widget_create endpoint.
    """

    # override the dependencies to use the mock service
    def override_get_widget_service():
        return mock_widget_service

    # override headers because authentication is outside of this unit test
    def override_authenticate_headers():
        return "Authenticated successfully."

    app.dependency_overrides[get_widget_service] = override_get_widget_service
    app.dependency_overrides[authenticate_headers] = override_authenticate_headers
    mock_widget_service.widget_create = AsyncMock(return_value=mock_widget_read)

    response = client.post(
        "/v1/upstream",
        headers={"X-API-Key": mock_api_key},
        json={"name": "Test Widget"},
    )
    assert response.status_code == 201
    assert response.json() == mock_widget_read.model_dump()

    # reset the dependency override
    app.dependency_overrides.pop(get_widget_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)


@pytest.mark.asyncio
async def test_get_widget_service_dependency():
    """
    Test the get_widget_service dependency.
    """
    # create properly typed mock dependencies
    mock_api_clients = {"widgets": AsyncMock(spec=httpx.AsyncClient)}

    # create a real SectionACL instance instead of MagicMock
    mock_acls = [
        SectionACL(
            permissions=["read"],
            section_regex=".*",
        )
    ]

    mock_settings = MagicMock(spec=AppSettings)
    mock_cache = MagicMock(spec=AppCacheBase)

    # call the dependency function directly
    widget_service = get_widget_service(
        api_clients=mock_api_clients,
        acls=mock_acls,
        settings=mock_settings,
        cache=mock_cache,
    )

    # Verify the service was created correctly
    assert isinstance(widget_service, WidgetApiService)
    assert isinstance(widget_service.widget_api_repository, WidgetApiRepository)
    assert (
        widget_service.widget_api_repository.api_client == mock_api_clients["widgets"]
    )
    assert widget_service.acls == mock_acls
    assert widget_service.settings == mock_settings
    assert widget_service.cache == mock_cache


@pytest.mark.asyncio
async def test_widget_get_by_id_endpoint_success(
    mock_api_key,
    mock_widget_service,
    mock_widget_read,
):
    """
    Unit test for the widget_get_by_id endpoint when the widget exists.
    """

    # override the dependencies to use the mock service
    def override_get_widget_service():
        return mock_widget_service

    # override headers because authentication is outside of this unit test
    def override_authenticate_headers():
        return "Authenticated successfully."

    app.dependency_overrides[get_widget_service] = override_get_widget_service
    app.dependency_overrides[authenticate_headers] = override_authenticate_headers
    mock_widget_service.widget_get_by_id = AsyncMock(return_value=mock_widget_read)

    response = client.get(
        f"/v1/upstream/{mock_widget_read.id}",
        headers={"X-API-Key": mock_api_key},
    )

    assert response.status_code == 200
    assert response.json() == mock_widget_read.model_dump()

    app.dependency_overrides.pop(get_widget_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)


@pytest.mark.asyncio
async def test_widget_get_by_id_endpoint_not_found(
    mock_api_key,
    mock_widget_service,
):
    """
    Unit test for the widget_get_by_id endpoint when the widget does not exist.
    """

    # override the dependencies to use the mock service
    def override_get_widget_service():
        return mock_widget_service

    # override headers because authentication is outside of this unit test
    def override_authenticate_headers():
        return "Authenticated successfully."

    app.dependency_overrides[get_widget_service] = override_get_widget_service
    app.dependency_overrides[authenticate_headers] = override_authenticate_headers
    mock_widget_service.widget_get_by_id = AsyncMock(
        side_effect=ResourceNotFoundError(resource_id=123, resource_name="Widget"),
    )

    response = client.get(
        "/v1/upstream/123",
        headers={"X-API-Key": mock_api_key},
    )
    assert response.status_code == 404

    app.dependency_overrides.pop(get_widget_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)


@pytest.mark.asyncio
async def test_widget_zap_endpoint_success(
    mock_api_key: str,
    mock_widget_service: AsyncMock,
    mock_widget_read: WidgetRead,
    mock_widget_zap_task: WidgetZapTask,
):
    """
    Unit test for the widget_zap endpoint.
    """

    # override the dependencies to use the mock service
    def override_get_widget_service():
        return mock_widget_service

    # override headers because authentication is outside of this unit test
    def override_authenticate_headers():
        return "Authenticated successfully."

    app.dependency_overrides[get_widget_service] = override_get_widget_service
    app.dependency_overrides[authenticate_headers] = override_authenticate_headers

    # mock the widget_zap methods
    mock_widget_service.widget_zap = AsyncMock(return_value=mock_widget_zap_task)

    response = client.post(
        f"/v1/upstream/{mock_widget_read.id}/zap",
        headers={"X-API-Key": mock_api_key},
        json={"duration": 1},
    )

    assert response.status_code == 202
    assert response.json() == mock_widget_zap_task.model_dump()

    # verify the service methods were called correctly
    mock_widget_service.widget_zap.assert_awaited_once_with(
        mock_widget_read.id, WidgetZap(duration=1)
    )

    # reset the dependency override
    app.dependency_overrides.pop(get_widget_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)


@pytest.mark.asyncio
async def test_widget_zap_endpoint_not_found(mock_api_key, mock_widget_service):
    """
    Unit test for the widget_zap endpoint when widget ID does not exist.
    """

    # override the dependencies to use the mock service
    def override_get_widget_service():
        return mock_widget_service

    # override headers because authentication is outside of this unit test
    def override_authenticate_headers():
        return "Authenticated successfully."

    app.dependency_overrides[get_widget_service] = override_get_widget_service
    app.dependency_overrides[authenticate_headers] = override_authenticate_headers
    mock_widget_service.widget_zap = AsyncMock(
        side_effect=ResourceNotFoundError(resource_id=123, resource_name="Widget"),
    )

    response = client.post(
        "/v1/upstream/123/zap",
        headers={"X-API-Key": mock_api_key},
        json={"duration": 1},
    )
    assert response.status_code == 404

    # reset the dependency override
    app.dependency_overrides.pop(get_widget_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)


@pytest.mark.asyncio
async def test_widget_zap_get_task_success(
    mock_api_key: str,
    mock_widget_zap_task: WidgetZapTask,
):
    """
    Test successful retrieval of zap task status.
    """
    # create fresh mock service
    mock_service = AsyncMock(spec=WidgetApiService)
    mock_service.widget_zap_by_uuid = AsyncMock(return_value=mock_widget_zap_task)

    # override dependencies
    def override_get_widget_service():
        return mock_service

    def override_authenticate_headers():
        return "Authenticated successfully."

    app.dependency_overrides[get_widget_service] = override_get_widget_service
    app.dependency_overrides[authenticate_headers] = override_authenticate_headers

    # make request
    response = client.get(
        f"/v1/upstream/1/zap/{mock_widget_zap_task.uuid}/status",
        headers={"X-API-Key": mock_api_key},
    )

    # verify response
    assert response.status_code == 200
    assert response.json() == mock_widget_zap_task.model_dump()
    mock_service.widget_zap_by_uuid.assert_awaited_once_with(
        1,
        mock_widget_zap_task.uuid,
    )
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_widget_zap_endpoint_status_not_found(
    mock_api_key,
    mock_widget_service,
):
    """
    Unit test for the widget_zap endpoint.
    """

    # override the dependencies to use the mock service
    def override_get_widget_service():
        return mock_widget_service

    # override headers because authentication is outside of this unit test
    def override_authenticate_headers():
        return "Authenticated successfully."

    app.dependency_overrides[get_widget_service] = override_get_widget_service
    app.dependency_overrides[authenticate_headers] = override_authenticate_headers
    mock_widget_service.widget_zap_by_uuid = AsyncMock(
        side_effect=ResourceNotFoundError(resource_id=123, resource_name="Widget"),
    )

    response = client.get(
        "/v1/upstream/123/zap/not-a-real-uuid/status",
        headers={"X-API-Key": mock_api_key},
    )
    assert response.status_code == 404

    # reset the dependency override
    app.dependency_overrides.pop(get_widget_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)
