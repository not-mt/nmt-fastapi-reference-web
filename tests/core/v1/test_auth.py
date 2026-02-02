# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for core authentication functions."""

from unittest.mock import AsyncMock, MagicMock, patch

import argon2
import pytest
from fastapi import HTTPException
from nmtfast.auth.v1.acl import AuthSuccess
from nmtfast.auth.v1.exceptions import AuthenticationError
from nmtfast.settings.v1.schemas import (
    AuthSettings,
    IncomingAuthApiKey,
    IncomingAuthSettings,
    SectionACL,
)

from app.core.v1.auth import process_api_key_header, process_bearer_token
from app.core.v1.settings import AppSettings

ph = argon2.PasswordHasher()


@pytest.fixture
def mock_api_key():
    """
    Fixture providing a test API key.
    """
    return "test-api-key"


@pytest.fixture
def mock_settings(mock_api_key):
    """
    Fixture providing properly configured AppSettings.
    """
    return AppSettings(
        auth=AuthSettings(
            swagger_token_url="http://localhost/token",
            id_providers={},
            incoming=IncomingAuthSettings(
                clients={},
                api_keys={
                    "valid-key": IncomingAuthApiKey(
                        contact="test@example.com",
                        memo="pytest fixture",
                        hash=ph.hash(mock_api_key),
                        algo="argon2",
                        acls=[SectionACL(section_regex=".*", permissions=["*"])],
                    )
                },
            ),
        ),
    )


@pytest.fixture
def mock_cache():
    """
    Fixture providing a mock cache implementation.
    """
    return MagicMock()


@pytest.fixture
def mock_acls():
    """
    Fixture providing sample ACL data.
    """
    return [SectionACL(section_regex=".*", permissions=["*"])]


@pytest.fixture
def mock_auth_info(mock_acls):
    """
    Fixture providing sample AuthSuccess (with list of SectionACLs).
    """
    return AuthSuccess(name="test-user", acls=mock_acls)


# Tests for process_api_key_header
@pytest.mark.asyncio
async def test_process_api_key_header_empty_key(mock_settings, mock_cache):
    """
    Test API key authentication fails with empty key.
    """
    # test mode "authn"
    with pytest.raises(HTTPException) as exc:
        await process_api_key_header("", mock_settings, mock_cache, "authn")
    assert exc.value.status_code == 403
    assert "Invalid API key" in exc.value.detail

    # test mode "authz"
    with pytest.raises(HTTPException) as exc:
        await process_api_key_header("", mock_settings, mock_cache, "authz")
    assert exc.value.status_code == 403
    assert "Invalid API key" in exc.value.detail


@pytest.mark.asyncio
async def test_process_api_key_header_cached_success(
    mock_settings, mock_cache, mock_acls
):
    """
    Test API key authentication with valid cached ACLs.
    """
    auth_info = AuthSuccess(name="valid-key", acls=mock_acls)
    mock_cache.fetch_app_cache.return_value = auth_info.model_dump_json()

    # test mode "authn"
    result = await process_api_key_header(
        "valid-key", mock_settings, mock_cache, "authn"
    )
    assert len(result) == 1
    assert result[0].permissions == ["*"]

    # test mode "authz"
    result = await process_api_key_header(
        "valid-key", mock_settings, mock_cache, "authz"
    )
    assert len(result) == 1
    assert result[0].permissions == ["*"]


@pytest.mark.asyncio
async def test_process_api_key_header_authn_cache_miss_success(
    mock_settings, mock_cache, mock_api_key
):
    """
    Test API key authentication with cache miss but successful authn.
    """
    # test mode "authn"
    mock_cache.fetch_app_cache.return_value = None
    result = await process_api_key_header(
        mock_api_key, mock_settings, mock_cache, "authn"
    )
    assert len(result) == 1
    assert result[0].permissions == ["*"]
    mock_cache.store_app_cache.assert_called_once()


@pytest.mark.asyncio
async def test_process_api_key_header_authz_cache_miss_success(
    mock_settings, mock_cache, mock_api_key
):
    """
    Test API key authentication with cache miss but successful authz.
    """
    # test mode "authz"
    mock_cache.fetch_app_cache.return_value = None
    result = await process_api_key_header(
        mock_api_key, mock_settings, mock_cache, "authz"
    )
    assert len(result) == 1
    assert result[0].permissions == ["*"]
    mock_cache.store_app_cache.assert_called_once()


@pytest.mark.asyncio
async def test_process_api_key_header_auth_error(mock_settings, mock_cache):
    """
    Test API key authentication with authentication error.
    """
    with patch(
        "app.core.v1.auth.authenticate_api_key",
        new=AsyncMock(side_effect=AuthenticationError("Invalid key")),
    ):
        # test mode "authn"
        mock_cache.fetch_app_cache.return_value = None
        with pytest.raises(HTTPException) as exc:
            await process_api_key_header(
                "invalid-key", mock_settings, mock_cache, "authn"
            )
        assert exc.value.status_code == 403
        assert "Invalid key" in exc.value.detail

        # test mode "authz"
        mock_cache.fetch_app_cache.return_value = None
        with pytest.raises(HTTPException) as exc:
            await process_api_key_header(
                "invalid-key", mock_settings, mock_cache, "authz"
            )
        assert exc.value.status_code == 403
        assert "Invalid key" in exc.value.detail


# Tests for process_bearer_token
@pytest.mark.asyncio
async def test_process_bearer_token_empty_token(mock_settings, mock_cache):
    """
    Test bearer token authentication with empty token.
    """
    # test mode authn
    with pytest.raises(HTTPException) as exc:
        await process_bearer_token("", mock_settings, mock_cache, "authn")
    assert exc.value.status_code == 401
    assert "Missing or invalid" in exc.value.detail

    # test mode authz
    with pytest.raises(HTTPException) as exc:
        await process_bearer_token("", mock_settings, mock_cache, "authz")
    assert exc.value.status_code == 401
    assert "Missing or invalid" in exc.value.detail


@pytest.mark.asyncio
async def test_process_bearer_token_invalid_format(mock_settings, mock_cache):
    """
    Test bearer token authentication with invalid JWT format.
    """
    # test mode authn
    with pytest.raises(HTTPException) as exc:
        await process_bearer_token(
            "invalid-token-format", mock_settings, mock_cache, "authn"
        )
    assert exc.value.status_code == 403
    assert "Invalid token" in exc.value.detail

    # test mode authz
    with pytest.raises(HTTPException) as exc:
        await process_bearer_token(
            "invalid-token-format", mock_settings, mock_cache, "authz"
        )
    assert exc.value.status_code == 403
    assert "Invalid token" in exc.value.detail


@pytest.mark.asyncio
async def test_process_bearer_token_cached_success(
    mock_settings, mock_cache, mock_acls
):
    """
    Test bearer token authentication with valid cached ACLs.
    """
    auth_info = AuthSuccess(name="valid.jwt.token", acls=mock_acls)
    mock_cache.fetch_app_cache.return_value = auth_info.model_dump_json()

    # test mode authn
    result = await process_bearer_token(
        "valid.jwt.token", mock_settings, mock_cache, "authn"
    )
    assert len(result) == 1
    assert result[0].permissions == ["*"]

    # test mode authz
    result = await process_bearer_token(
        "valid.jwt.token", mock_settings, mock_cache, "authz"
    )
    assert len(result) == 1
    assert result[0].permissions == ["*"]


@pytest.mark.asyncio
async def test_process_bearer_token_authn_cache_miss_success(
    mock_settings, mock_cache, mock_auth_info
):
    """
    Test bearer token authentication with cache miss but successful authn.
    """
    with patch(
        "app.core.v1.auth.authenticate_token",
        new=AsyncMock(return_value=mock_auth_info),
    ):
        # test mode authn
        mock_cache.fetch_app_cache.return_value = None
        result = await process_bearer_token(
            "valid.jwt.token", mock_settings, mock_cache, "authn"
        )
        assert len(result) == 1
        mock_cache.store_app_cache.assert_called_once()


@pytest.mark.asyncio
async def test_process_bearer_token_authz_cache_miss_success(
    mock_settings, mock_cache, mock_auth_info
):
    """
    Test bearer token authentication with cache miss but successful authz.
    """
    with patch(
        "app.core.v1.auth.authenticate_token",
        new=AsyncMock(return_value=mock_auth_info),
    ):
        # test mode authz
        mock_cache.fetch_app_cache.return_value = None
        result = await process_bearer_token(
            "valid.jwt.token", mock_settings, mock_cache, "authz"
        )
        assert len(result) == 1
        mock_cache.store_app_cache.assert_called_once()


@pytest.mark.asyncio
async def test_process_bearer_token_auth_error(mock_settings, mock_cache):
    """
    Test bearer token authentication with authentication error.
    """
    mock_cache.fetch_app_cache.return_value = None
    with patch(
        "app.core.v1.auth.authenticate_token",
        new=AsyncMock(side_effect=AuthenticationError("Invalid token")),
    ):
        # test mode authn
        with pytest.raises(HTTPException) as exc:
            await process_bearer_token(
                "invalid.jwt.token", mock_settings, mock_cache, "authn"
            )
        assert exc.value.status_code == 403
        assert "Invalid token" in exc.value.detail

        # test mode authz
        with pytest.raises(HTTPException) as exc:
            await process_bearer_token(
                "invalid.jwt.token", mock_settings, mock_cache, "authz"
            )
        assert exc.value.status_code == 403
        assert "Invalid token" in exc.value.detail


@pytest.mark.asyncio
async def test_process_bearer_token_no_acls_returned(mock_settings, mock_cache):
    """
    Test bearer token authentication when no ACLs are returned.
    """
    with patch("app.core.v1.auth.authenticate_token", new=AsyncMock(return_value=[])):
        # test mode authn
        mock_cache.fetch_app_cache.return_value = None
        with pytest.raises(HTTPException) as exc:
            await process_bearer_token(
                "valid.jwt.token", mock_settings, mock_cache, "authn"
            )
        assert exc.value.status_code == 403
        assert "no permissions" in exc.value.detail

        # test mode authz
        mock_cache.fetch_app_cache.return_value = None
        with pytest.raises(HTTPException) as exc:
            await process_bearer_token(
                "valid.jwt.token", mock_settings, mock_cache, "authz"
            )
        assert exc.value.status_code == 403
        assert "no permissions" in exc.value.detail


@pytest.mark.asyncio
async def test_process_api_key_header_auth_returns_no_acls(
    mock_settings, mock_cache, mock_api_key
):
    """
    Test API key authentication when authenticate_api_key returns no ACLs.
    """
    with patch(
        "app.core.v1.auth.authenticate_api_key", new=AsyncMock(return_value=[])
    ):  # explicitly return empty list

        # test mode "authn"
        mock_cache.fetch_app_cache.return_value = None
        result = await process_api_key_header(
            mock_api_key, mock_settings, mock_cache, "authn"
        )
        assert result == []
        mock_cache.store_app_cache.assert_not_called()  # should not store empty ACLs

        # test mode "authz"
        mock_cache.fetch_app_cache.return_value = None
        result = await process_api_key_header(
            mock_api_key, mock_settings, mock_cache, "authz"
        )
        assert result == []
        mock_cache.store_app_cache.assert_not_called()  # should not store empty ACLs
