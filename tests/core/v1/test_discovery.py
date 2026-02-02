# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Tests for service discovery provisioning."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.discovery.v1.exceptions import ServiceConnectionError

from app.core.v1.discovery import api_clients, create_api_clients
from app.core.v1.settings import AppSettings


@pytest.fixture
def mock_settings():
    """
    Fixture to create a mock AppSettings.
    """
    settings = MagicMock(spec=AppSettings)
    settings.auth = "mock_auth"
    settings.discovery = "mock_discovery"
    return settings


@pytest.fixture
def mock_cache():
    """
    Fixture to create a mock app_cache.
    """
    return AsyncMock(spec=AppCacheBase)


@pytest.fixture(autouse=True)
def setup_teardown():
    """
    Clear api_clients before and after each test.
    """
    api_clients.clear()
    yield
    api_clients.clear()


@pytest.mark.asyncio
async def test_create_api_clients_success(mock_settings, mock_cache):
    """
    Test successful client creation.
    """
    with (
        patch("app.core.v1.discovery.get_app_settings", return_value=mock_settings),
        patch("app.core.v1.discovery.app_cache", mock_cache),
        patch(
            "app.core.v1.discovery.create_api_client", new_callable=AsyncMock
        ) as mock_create,
    ):

        mock_client = AsyncMock(httpx.AsyncClient)
        mock_create.return_value = mock_client

        await create_api_clients()

        assert len(api_clients) == 1
        assert "widgets" in api_clients
        assert api_clients["widgets"] is mock_client


@pytest.mark.asyncio
async def test_create_api_clients_failure(mock_settings, mock_cache):
    """
    Test client creation failure.
    """
    with (
        patch(
            "app.core.v1.discovery.get_app_settings",
            return_value=mock_settings,
        ),
        patch(
            "app.core.v1.discovery.app_cache",
            mock_cache,
        ),
        patch(
            "app.core.v1.discovery.create_api_client",
            side_effect=ServiceConnectionError,
        ),
    ):
        with pytest.raises(ServiceConnectionError):
            await create_api_clients()

        assert not api_clients  # no clients stored on failure


@pytest.mark.asyncio
async def test_create_api_clients_cleanup_on_failure(mock_settings, mock_cache):
    """
    Test existing clients are closed on failure.
    """
    existing_client = AsyncMock()
    api_clients["existing"] = existing_client

    with (
        patch(
            "app.core.v1.discovery.get_app_settings",
            return_value=mock_settings,
        ),
        patch(
            "app.core.v1.discovery.app_cache",
            mock_cache,
        ),
        patch(
            "app.core.v1.discovery.create_api_client",
            side_effect=ServiceConnectionError,
        ),
    ):
        with pytest.raises(ServiceConnectionError):
            await create_api_clients()

        existing_client.aclose.assert_called_once()
