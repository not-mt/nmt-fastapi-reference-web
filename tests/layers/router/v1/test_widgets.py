# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for router layer."""

from unittest.mock import AsyncMock

import pytest
from aiokafka import AIOKafkaProducer
from fastapi.testclient import TestClient
from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.settings.v1.schemas import SectionACL
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.v1.settings import AppSettings
from app.dependencies.v1.sqlalchemy import get_sql_db
from app.errors.v1.exceptions import ResourceNotFoundError
from app.layers.repository.v1.widgets import WidgetRepository
from app.layers.router.v1.widgets import authenticate_headers, get_widget_service
from app.layers.service.v1.widgets import WidgetService
from app.main import app
from app.schemas.dto.v1.widgets import WidgetRead, WidgetZapTask

client = TestClient(app)


@pytest.fixture
def mock_async_session() -> AsyncMock:
    """
    Fixture to provide a mock AsyncSession.
    """
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_cache():
    """
    Fixture to generate a mock app cache.
    """
    return AsyncMock(spec=AppCacheBase)


@pytest.fixture
def mock_kafka():
    """
    Fixture to generate a mock Kafka producer.
    """
    return AsyncMock(spec=AIOKafkaProducer)


@pytest.fixture
def mock_widget_repository(mock_async_session: AsyncMock) -> WidgetRepository:
    """
    Fixture to provide a mock WidgetRepository.
    """
    return WidgetRepository(mock_async_session)


@pytest.fixture
def mock_widget_service(
    mock_widget_repository: WidgetRepository,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_kafka: AIOKafkaProducer,
) -> WidgetService:
    """
    Fixture to provide a mock WidgetService.
    """
    return WidgetService(
        mock_widget_repository,
        mock_allow_acls,
        mock_settings,
        mock_cache,
        mock_kafka,
    )


@pytest.fixture
def mock_widget_read() -> WidgetRead:
    """
    Fixture to provide a test WidgetRead instance.
    """
    return WidgetRead(id=1, name="Test Widget", height="10", mass="5", force=20)


@pytest.fixture
def mock_widget_zap_task() -> WidgetZapTask:
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
    mock_api_key: str,
    mock_widget_service: AsyncMock,
    mock_widget_read: WidgetRead,
):
    """Unit test for the widget_create endpoint."""

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
        "/v1/widgets/",
        headers={"X-API-Key": mock_api_key},
        json={"name": "Test Widget"},
    )
    assert response.status_code == 201
    assert response.json() == mock_widget_read.model_dump()

    # Reset the dependency override
    app.dependency_overrides.pop(get_widget_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)


@pytest.mark.asyncio
async def test_get_widget_service_dependency(mock_async_session: AsyncMock):
    """Test the get_widget_service dependency."""

    # Override the database dependency to use a mock session
    def override_get_sql_db():
        return mock_async_session

    app.dependency_overrides[get_sql_db] = override_get_sql_db

    widget_service = get_widget_service(mock_async_session)

    assert isinstance(widget_service, WidgetService)
    assert isinstance(widget_service.widget_repository, WidgetRepository)
    assert widget_service.widget_repository.db == mock_async_session

    app.dependency_overrides.pop(get_sql_db)


@pytest.mark.asyncio
async def test_widget_get_by_id_endpoint_success(
    mock_api_key: str,
    mock_widget_service: AsyncMock,
    mock_widget_read: WidgetRead,
):
    """Unit test for the widget_get_by_id endpoint when the widget exists."""

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
        f"/v1/widgets/{mock_widget_read.id}",
        headers={"X-API-Key": mock_api_key},
    )

    assert response.status_code == 200
    assert response.json() == mock_widget_read.model_dump()

    app.dependency_overrides.pop(get_widget_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)


@pytest.mark.asyncio
async def test_widget_get_by_id_endpoint_not_found(
    mock_api_key: str,
    mock_widget_service: AsyncMock,
):
    """Unit test for the widget_get_by_id endpoint when the widget does not exist."""

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
        "/v1/widgets/123",
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
    """Unit test for the widget_zap endpoint."""

    # override the dependencies to use the mock service
    def override_get_widget_service():
        return mock_widget_service

    # override headers because authentication is outside of this unit test
    def override_authenticate_headers():
        return "Authenticated successfully."

    app.dependency_overrides[get_widget_service] = override_get_widget_service
    app.dependency_overrides[authenticate_headers] = override_authenticate_headers
    mock_widget_service.widget_get_by_id = AsyncMock(return_value=mock_widget_read)

    response = client.post(
        f"/v1/widgets/{mock_widget_read.id}/zap",
        headers={"X-API-Key": mock_api_key},
        json={"duration": 1},
    )
    assert response.status_code == 202
    assert response.json()["state"] == mock_widget_zap_task.model_dump()["state"]

    # Reset the dependency override
    app.dependency_overrides.pop(get_widget_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)


@pytest.mark.asyncio
async def test_widget_zap_endpoint_not_found(
    mock_api_key: str,
    mock_widget_service: AsyncMock,
):
    """Unit test for the widget_zap endpoint when widget ID does not exist."""

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
        "/v1/widgets/123/zap",
        headers={"X-API-Key": mock_api_key},
        json={"duration": 1},
    )
    assert response.status_code == 404

    # Reset the dependency override
    app.dependency_overrides.pop(get_widget_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)


@pytest.mark.asyncio
async def test_widget_zap_endpoint_status_success(
    mock_api_key: str,
    mock_widget_service: AsyncMock,
    mock_widget_read: WidgetRead,
    mock_widget_zap_task: WidgetZapTask,
):
    """Unit test for the widget_zap endpoint."""

    # override the dependencies to use the mock service
    def override_get_widget_service():
        return mock_widget_service

    # override headers because authentication is outside of this unit test
    def override_authenticate_headers():
        return "Authenticated successfully."

    app.dependency_overrides[get_widget_service] = override_get_widget_service
    app.dependency_overrides[authenticate_headers] = override_authenticate_headers
    mock_widget_service.widget_get_by_id = AsyncMock(return_value=mock_widget_read)

    response = client.post(
        f"/v1/widgets/{mock_widget_read.id}/zap",
        headers={"X-API-Key": mock_api_key},
        json={"duration": 1},
    )
    assert response.status_code == 202
    assert response.json()["state"] == mock_widget_zap_task.model_dump()["state"]

    uuid = response.json()["uuid"]
    response = client.get(
        f"/v1/widgets/{mock_widget_read.id}/zap/{uuid}/status",
        headers={"X-API-Key": mock_api_key},
    )
    assert response.status_code == 200
    assert response.json()["uuid"] == uuid

    # Reset the dependency override
    app.dependency_overrides.pop(get_widget_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)


@pytest.mark.asyncio
async def test_widget_zap_endpoint_status_not_found(
    mock_api_key: str,
    mock_widget_service: AsyncMock,
):
    """Unit test for the widget_zap endpoint."""

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
        "/v1/widgets/123/zap/not-a-real-uuid/status",
        headers={"X-API-Key": mock_api_key},
    )
    assert response.status_code == 404

    # Reset the dependency override
    app.dependency_overrides.pop(get_widget_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)
