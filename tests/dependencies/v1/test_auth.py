# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request
from nmtfast.auth.v1.exceptions import AuthenticationError
from nmtfast.settings.v1.schemas import SectionACL

from app.dependencies.v1.auth import authenticate_headers, get_acls


@pytest.fixture
def mock_settings():
    return MagicMock()


@pytest.fixture
def mock_cache():
    return AsyncMock()


@pytest.mark.asyncio
async def test_authenticate_headers_both_credentials_fail(mock_settings, mock_cache):
    """
    Test mutual exclusion of API key and token.
    """
    with pytest.raises(HTTPException) as exc:
        await authenticate_headers(
            api_key="test-key",
            token="test-token",
            settings=mock_settings,
            cache=mock_cache,
        )

    assert exc.value.status_code == 403
    assert "mutually exclusive" in exc.value.detail


@pytest.mark.asyncio
async def test_authenticate_headers_api_key_success(mock_settings, mock_cache):
    """
    Test successful API key authentication.
    """
    with patch(
        "app.dependencies.v1.auth.process_api_key_header",
        new=AsyncMock(
            return_value=[
                SectionACL(section_regex=".*", permissions=["*"]),
            ],
        ),
    ):
        result = await authenticate_headers(
            api_key="valid-key", token=None, settings=mock_settings, cache=mock_cache
        )
        assert "API key" in result


@pytest.mark.asyncio
async def test_authenticate_headers_api_key_failure(mock_settings, mock_cache):
    """
    Test failed API key authentication.
    """
    with patch(
        "app.dependencies.v1.auth.process_api_key_header",
        new=AsyncMock(side_effect=AuthenticationError("Invalid key")),
    ):
        with pytest.raises(HTTPException) as exc:
            await authenticate_headers(
                api_key="invalid-key",
                token=None,
                settings=mock_settings,
                cache=mock_cache,
            )

        assert exc.value.status_code == 403
        assert "Invalid API key" in exc.value.detail


@pytest.mark.asyncio
async def test_authenticate_headers_api_key_no_acls(mock_settings, mock_cache):
    """
    Test API key authentication with no ACLs.
    """
    with patch(
        "app.dependencies.v1.auth.process_api_key_header",
        new=AsyncMock(return_value=[]),
    ):
        with pytest.raises(HTTPException) as exc:
            await authenticate_headers(
                api_key="no-acls-key",
                token=None,
                settings=mock_settings,
                cache=mock_cache,
            )
        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_authenticate_headers_token_success(mock_settings, mock_cache):
    """
    Test successful token authentication.
    """
    with patch(
        "app.dependencies.v1.auth.process_bearer_token",
        new=AsyncMock(
            return_value=[SectionACL(section_regex=".*", permissions=["*"])],
        ),
    ):
        result = await authenticate_headers(
            api_key=None,
            token="valid.token.here",
            settings=mock_settings,
            cache=mock_cache,
        )
        assert "Bearer token" in result


@pytest.mark.asyncio
async def test_authenticate_headers_token_failure(mock_settings, mock_cache):
    """
    Test failed token authentication.
    """
    with patch(
        "app.dependencies.v1.auth.process_bearer_token",
        new=AsyncMock(side_effect=AuthenticationError("Invalid token")),
    ):
        with pytest.raises(HTTPException) as exc:
            await authenticate_headers(
                api_key=None,
                token="invalid.token",
                settings=mock_settings,
                cache=mock_cache,
            )
        assert exc.value.status_code == 403
        assert "Invalid token" in exc.value.detail


@pytest.mark.asyncio
async def test_authenticate_headers_no_credentials(mock_settings, mock_cache):
    """
    Test no credentials provided.
    """
    with pytest.raises(HTTPException) as exc:
        await authenticate_headers(
            api_key=None, token=None, settings=mock_settings, cache=mock_cache
        )

    assert exc.value.status_code == 403
    assert "Missing" in exc.value.detail


@pytest.mark.asyncio
async def test_get_acls_api_key_success(mock_settings, mock_cache):
    """
    Test successful ACL retrieval with API key.
    """
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {"X-API-Key": "valid-key"}

    with patch(
        "app.dependencies.v1.auth.process_api_key_header",
        new=AsyncMock(
            return_value=[
                SectionACL(section_regex=".*", permissions=["*"]),
            ],
        ),
    ):
        result = await get_acls(mock_request, mock_settings, mock_cache)
        assert len(result) == 1
        assert result[0].permissions == ["*"]


@pytest.mark.asyncio
async def test_get_acls_api_key_failure(mock_settings, mock_cache):
    """
    Test failed ACL retrieval with API key.
    """
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {"X-API-Key": "invalid-key"}

    with patch(
        "app.dependencies.v1.auth.process_api_key_header",
        new=AsyncMock(side_effect=AuthenticationError("Invalid key")),
    ):
        with pytest.raises(HTTPException) as exc:
            await get_acls(mock_request, mock_settings, mock_cache)

        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_acls_token_success(mock_settings, mock_cache):
    """
    Test successful ACL retrieval with token.
    """
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {"Authorization": "Bearer valid.token.here"}

    with patch(
        "app.dependencies.v1.auth.process_bearer_token",
        new=AsyncMock(
            return_value=[
                SectionACL(section_regex=".*", permissions=["*"]),
            ],
        ),
    ):
        result = await get_acls(mock_request, mock_settings, mock_cache)

        assert len(result) == 1
        assert result[0].permissions == ["*"]


@pytest.mark.asyncio
async def test_get_acls_token_failure(mock_settings, mock_cache):
    """
    Test failed ACL retrieval with token.
    """
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {"Authorization": "Bearer invalid.token"}

    with patch(
        "app.dependencies.v1.auth.process_bearer_token",
        new=AsyncMock(side_effect=AuthenticationError("Invalid token")),
    ):
        with pytest.raises(HTTPException) as exc:
            await get_acls(mock_request, mock_settings, mock_cache)

        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_acls_invalid_token_format(mock_settings, mock_cache):
    """
    Test invalid token format.
    """
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {"Authorization": "Bearer invalid-token-format"}

    with pytest.raises(HTTPException) as exc:
        await get_acls(mock_request, mock_settings, mock_cache)

    assert exc.value.status_code == 403
    assert "Invalid token" in exc.value.detail


@pytest.mark.asyncio
async def test_get_acls_no_bearer_prefix(mock_settings, mock_cache):
    """
    Test token without Bearer prefix.
    """
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {"Authorization": "not-a-bearer-token"}

    with pytest.raises(HTTPException) as exc:
        await get_acls(mock_request, mock_settings, mock_cache)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_acls_no_credentials(mock_settings, mock_cache):
    """
    Test no credentials provided.
    """
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {}

    with pytest.raises(HTTPException) as exc:
        await get_acls(mock_request, mock_settings, mock_cache)

    assert exc.value.status_code == 403
    assert "Unauthorized" in exc.value.detail


@pytest.mark.asyncio
async def test_get_acls_empty_token(mock_settings, mock_cache):
    """
    Test empty Bearer token.
    """
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {"Authorization": "Bearer "}

    with pytest.raises(HTTPException) as exc:
        await get_acls(mock_request, mock_settings, mock_cache)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_authenticate_headers_token_no_acls(mock_settings, mock_cache):
    """
    Test token authentication returns no ACLs.
    """
    with patch(
        "app.dependencies.v1.auth.process_bearer_token", new=AsyncMock(return_value=[])
    ):
        with pytest.raises(HTTPException) as exc:
            await authenticate_headers(
                api_key=None,
                token="valid.but.empty.acls",
                settings=mock_settings,
                cache=mock_cache,
            )

        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_acls_token_auth_error(mock_settings, mock_cache):
    """
    Test token authentication raises AuthenticationError.
    """
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {"Authorization": "Bearer valid.but.error"}

    with patch(
        "app.dependencies.v1.auth.process_bearer_token",
        new=AsyncMock(side_effect=AuthenticationError("Token validation failed")),
    ):
        with pytest.raises(HTTPException) as exc:
            await get_acls(mock_request, mock_settings, mock_cache)

        assert exc.value.status_code == 403
        assert "Token validation failed" in exc.value.detail
