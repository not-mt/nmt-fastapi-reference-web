# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for cache dependency injection functions."""

from unittest.mock import MagicMock, patch

import pytest
from nmtfast.cache.v1.base import AppCacheBase

from app.core.v1.settings import AppSettings
from app.dependencies.v1.cache import get_cache


@pytest.fixture
def mock_settings():
    """
    Fixture providing mock application settings.
    """
    return MagicMock(spec=AppSettings)


@pytest.fixture
def mock_cache():
    """
    Fixture providing a mock cache implementation.
    """
    return MagicMock(spec=AppCacheBase)


@pytest.mark.asyncio
async def test_get_cache_returns_app_cache(mock_settings, mock_cache):
    """
    Test get_cache returns the app_cache instance.
    """
    with patch("app.dependencies.v1.cache.app_cache", new=mock_cache):
        result = await get_cache(mock_settings)
        assert result == mock_cache
