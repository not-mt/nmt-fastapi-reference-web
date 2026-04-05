# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for the WebUI service layer."""

from unittest.mock import AsyncMock

import pytest
from nmtfast.auth.v1.exceptions import AuthorizationError
from nmtfast.cache.v1.base import AppCacheBase

from app.layers.service.v1.main import WebUIService


@pytest.fixture
def webui_service(mock_allow_acls, mock_settings):
    """
    Fixture to provide a WebUIService instance.
    """
    cache = AsyncMock(spec=AppCacheBase)
    return WebUIService(mock_allow_acls, mock_settings, cache, kafka=None)


@pytest.mark.asyncio
async def test_dummy_index_returns_none(webui_service):
    """
    Test that dummy_index returns None.
    """
    result = await webui_service.dummy_index()
    assert result is None


@pytest.mark.asyncio
async def test_is_authz_with_allowed_acls(webui_service):
    """
    Test that _is_authz passes with wildcard ACLs.
    """
    await webui_service._is_authz(webui_service.acls, "view")


@pytest.mark.asyncio
async def test_is_authz_with_denied_acls(mock_deny_acls, mock_settings):
    """
    Test that _is_authz raises AuthorizationError with restrictive ACLs.
    """
    cache = AsyncMock(spec=AppCacheBase)
    service = WebUIService(mock_deny_acls, mock_settings, cache, kafka=None)

    with pytest.raises(AuthorizationError):
        await service._is_authz(service.acls, "view")
