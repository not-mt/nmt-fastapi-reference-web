# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Tests for API client dependencies."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.v1.settings import AppSettings
from app.dependencies.v1.discovery import get_api_clients

# from fastapi import Depends


@pytest.fixture
def mock_clients():
    """
    Fixture providing mock API clients.
    """
    return {"service1": MagicMock(), "service2": MagicMock()}


@pytest.fixture(autouse=True)
def patch_dependencies(mock_clients):
    """
    Patch all dependencies.
    """
    with (
        patch("app.dependencies.v1.discovery.api_clients", mock_clients),
        patch("app.dependencies.v1.discovery.get_app_settings") as mock_settings,
    ):
        mock_settings.return_value = MagicMock(spec=AppSettings)
        yield


@pytest.mark.asyncio
async def test_get_api_clients_returns_clients(mock_clients):
    """
    Test that get_api_clients returns the api_clients dict.
    """
    result = await get_api_clients()
    assert result is mock_clients
