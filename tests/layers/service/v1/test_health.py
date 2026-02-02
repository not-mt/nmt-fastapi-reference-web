# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for AppHealthService."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.layers.service.v1.health import AppHealthService


@pytest.fixture
def mock_settings():
    return MagicMock()


@pytest.fixture
def mock_db():
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = None
    return db


@pytest.fixture
def mock_widget_repository(mock_db):
    repo = MagicMock()
    repo.db = mock_db
    return repo


@pytest.fixture
def mock_cache():
    cache = MagicMock()
    cache.fetch_app_cache.return_value = json.dumps("HEALTHY").encode("utf-8")
    return cache


@pytest.fixture
def service(mock_settings, mock_widget_repository, mock_cache):
    return AppHealthService(mock_settings, mock_widget_repository, mock_cache)


@pytest.mark.asyncio
async def test_check_database_success(service, mock_widget_repository):
    result = await service._check_database()
    assert result is True
    mock_widget_repository.db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_check_database_failure(service, mock_widget_repository):
    mock_widget_repository.db.execute.side_effect = OperationalError(
        "SELECT 1", {}, Exception("fail")
    )

    with pytest.raises(Exception):
        await service._check_database()


@pytest.mark.asyncio
async def test_check_cache_success(service, mock_cache):
    result = await service._check_cache()
    assert result is True
    mock_cache.store_app_cache.assert_called_once_with(
        "app_cache_health", json.dumps("HEALTHY")
    )
    mock_cache.fetch_app_cache.assert_called_once_with("app_cache_health")


@pytest.mark.asyncio
async def test_check_cache_failure_fetch(service, mock_cache):
    mock_cache.fetch_app_cache.return_value = json.dumps("UNHEALTHY").encode("utf-8")

    with pytest.raises(Exception):
        await service._check_cache()


@pytest.mark.asyncio
async def test_check_cache_failure_store(service, mock_cache):
    mock_cache.store_app_cache.side_effect = Exception("store fail")

    with pytest.raises(Exception):
        await service._check_cache()


@pytest.mark.asyncio
async def test_check_health_basic(service):
    result = await service.check_health(checks=["basic"])
    assert result is True


@pytest.mark.asyncio
async def test_check_health_database(service):
    result = await service.check_health(checks=["database"])
    assert result is True


@pytest.mark.asyncio
async def test_check_health_cache(service):
    result = await service.check_health(checks=["cache"])
    assert result is True


@pytest.mark.asyncio
async def test_check_health_all(service):
    result = await service.check_health(checks=["basic", "database", "cache"])
    assert result is True


@pytest.mark.asyncio
async def test_check_health_fails_on_database(service, mock_widget_repository):
    mock_widget_repository.db.execute.side_effect = Exception("fail")

    result = await service.check_health(checks=["database"])
    assert result is False


@pytest.mark.asyncio
async def test_check_health_fails_on_cache(service, mock_cache):
    mock_cache.fetch_app_cache.return_value = json.dumps("CORRUPT").encode("utf-8")

    result = await service.check_health(checks=["cache"])
    assert result is False
