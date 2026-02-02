# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for health check router."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.layers.repository.v1.widgets import WidgetRepository
from app.layers.router.v1.health import get_health_service
from app.layers.service.v1.health import AppHealthService
from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_health_service_true() -> AsyncMock:
    """
    Fixture to provide a healthy AppHealthService mock.
    """
    service = AsyncMock(spec=AppHealthService)
    service.check_health.return_value = True
    return service


@pytest.fixture
def mock_health_service_false() -> AsyncMock:
    """
    Fixture to provide an unhealthy AppHealthService mock.
    """
    service = AsyncMock(spec=AppHealthService)
    service.check_health.return_value = False
    return service


def test_get_health_service_creates_app_health_service():
    """
    Test that get_health_service() returns a valid AppHealthService
    with the expected injected dependencies.
    """
    mock_settings = MagicMock()
    mock_db = MagicMock()
    mock_cache = MagicMock()

    service = get_health_service(
        settings=mock_settings,
        db=mock_db,
        cache=mock_cache,
    )

    assert isinstance(service, AppHealthService)
    assert service.settings is mock_settings
    assert service.cache is mock_cache
    assert isinstance(service.widget_repository, WidgetRepository)
    assert service.widget_repository.db is mock_db


@pytest.mark.asyncio
async def test_liveness_healthy(mock_health_service_true: AsyncMock):
    """
    Test /health/liveness returns 200 when dependencies are healthy.
    """

    def override_get_health_service():
        return mock_health_service_true

    app.dependency_overrides[get_health_service] = override_get_health_service

    response = client.get("/health/liveness")
    assert response.status_code == 200

    app.dependency_overrides.pop(get_health_service, None)


@pytest.mark.asyncio
async def test_liveness_unhealthy(mock_health_service_false: AsyncMock):
    """
    Test /health/liveness returns 503 when dependencies are unhealthy.
    """

    def override_get_health_service():
        return mock_health_service_false

    app.dependency_overrides[get_health_service] = override_get_health_service

    response = client.get("/health/liveness")
    assert response.status_code == 503

    app.dependency_overrides.pop(get_health_service, None)


@pytest.mark.asyncio
@patch("app.layers.router.v1.health.check_app_readiness", return_value=True)
async def test_readiness_healthy(
    mock_check: AsyncMock, mock_health_service_true: AsyncMock
):
    """
    Test /health/readiness returns 200 when both app and dependencies are healthy.
    """

    def override_get_health_service():
        return mock_health_service_true

    app.dependency_overrides[get_health_service] = override_get_health_service

    response = client.get("/health/readiness")
    assert response.status_code == 200

    app.dependency_overrides.pop(get_health_service, None)


@pytest.mark.asyncio
@patch("app.layers.router.v1.health.check_app_readiness", return_value=False)
async def test_readiness_check_app_readiness_false(
    mock_check: AsyncMock, mock_health_service_true: AsyncMock
):
    """
    Test /health/readiness returns 503 when check_app_readiness() is False.
    """

    def override_get_health_service():
        return mock_health_service_true

    app.dependency_overrides[get_health_service] = override_get_health_service

    response = client.get("/health/readiness")
    assert response.status_code == 503

    app.dependency_overrides.pop(get_health_service, None)


@pytest.mark.asyncio
@patch("app.layers.router.v1.health.check_app_readiness", return_value=True)
async def test_readiness_unhealthy_dependencies(
    mock_check: AsyncMock, mock_health_service_false: AsyncMock
):
    """
    Test /health/readiness returns 503 when dependencies are not ready.
    """

    def override_get_health_service():
        return mock_health_service_false

    app.dependency_overrides[get_health_service] = override_get_health_service

    response = client.get("/health/readiness")
    assert response.status_code == 503

    app.dependency_overrides.pop(get_health_service, None)
