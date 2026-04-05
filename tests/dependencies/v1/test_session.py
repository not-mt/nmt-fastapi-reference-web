# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for session dependency functions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nmtfast.auth.v1.sessions import SessionData, SessionManager
from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.settings.v1.schemas import (
    AuthSettings,
    IDProvider,
    SessionSettings,
    WebAuthClientSettings,
)

from app.core.v1.settings import AppSettings
from app.dependencies.v1.session import get_current_session, get_session_manager


def test_get_session_manager_returns_none_when_no_session_config():
    """
    Test that get_session_manager returns None when session is not configured.
    """
    settings = MagicMock(spec=AppSettings)
    settings.auth = AuthSettings(
        swagger_token_url="https://example.com/token",
        id_providers={},
    )
    cache = MagicMock(spec=AppCacheBase)

    result = get_session_manager(settings=settings, cache=cache)
    assert result is None


def test_get_session_manager_returns_session_manager():
    """
    Test that get_session_manager returns a SessionManager when configured.
    """
    settings = MagicMock(spec=AppSettings)
    settings.auth = AuthSettings(
        swagger_token_url="https://example.com/token",
        id_providers={},
        session=SessionSettings(session_ttl=3600),
    )
    cache = MagicMock(spec=AppCacheBase)

    result = get_session_manager(settings=settings, cache=cache)
    assert isinstance(result, SessionManager)


@pytest.fixture
def session_settings():
    """
    Fixture providing SessionSettings for tests.
    """
    return SessionSettings(session_ttl=3600, cookie_name="session_id")


@pytest.fixture
def settings_with_session(session_settings):
    """
    Fixture providing AppSettings with session configured.
    """
    settings = MagicMock()
    settings.auth.session = session_settings
    settings.auth.web_auth = None
    return settings


@pytest.mark.asyncio
async def test_get_current_session_returns_none_when_no_manager(settings_with_session):
    """
    Test that get_current_session returns None when session_mgr is None.
    """
    request = MagicMock()

    result = await get_current_session(
        request=request, settings=settings_with_session, session_mgr=None
    )
    assert result is None


@pytest.mark.asyncio
async def test_get_current_session_returns_none_when_no_session_settings():
    """
    Test that get_current_session returns None when session settings are None.
    """
    request = MagicMock()
    settings = MagicMock()
    settings.auth.session = None
    session_mgr = MagicMock(spec=SessionManager)

    result = await get_current_session(
        request=request, settings=settings, session_mgr=session_mgr
    )
    assert result is None


@pytest.mark.asyncio
async def test_get_current_session_returns_none_when_no_cookie(settings_with_session):
    """
    Test that get_current_session returns None when no session cookie is present.
    """
    request = MagicMock()
    request.cookies = {}
    session_mgr = MagicMock(spec=SessionManager)

    result = await get_current_session(
        request=request, settings=settings_with_session, session_mgr=session_mgr
    )
    assert result is None


@pytest.mark.asyncio
async def test_get_current_session_returns_none_when_session_not_found(
    settings_with_session,
):
    """
    Test that get_current_session returns None when session is not in cache.
    """
    request = MagicMock()
    request.cookies = {"session_id": "some-session-id"}
    session_mgr = MagicMock(spec=SessionManager)
    session_mgr.get_session.return_value = None

    result = await get_current_session(
        request=request, settings=settings_with_session, session_mgr=session_mgr
    )
    assert result is None


@pytest.mark.asyncio
async def test_get_current_session_returns_session_no_refresh(settings_with_session):
    """
    Test that get_current_session returns the session when no refresh is needed.
    """
    request = MagicMock()
    request.cookies = {"session_id": "some-session-id"}

    session_data = MagicMock(spec=SessionData)
    session_mgr = MagicMock(spec=SessionManager)
    session_mgr.get_session.return_value = session_data

    result = await get_current_session(
        request=request, settings=settings_with_session, session_mgr=session_mgr
    )
    assert result is session_data


@pytest.mark.asyncio
async def test_get_current_session_refreshes_expired_token():
    """
    Test that get_current_session refreshes an expired token when configured.
    """
    request = MagicMock()
    request.cookies = {"session_id": "some-session-id"}

    session_settings = SessionSettings(session_ttl=3600, cookie_name="session_id")
    web_auth = WebAuthClientSettings(
        provider="test-idp",
        client_id="client-id",
        client_secret="secret",
        redirect_uri="http://localhost/callback",
        scopes=["openid"],
        refresh_enabled=True,
    )
    provider = IDProvider(
        type="jwks",
        issuer_regex=r"^https://idp\.example\.com$",
        jwks_endpoint="https://idp.example.com/jwks",
        token_endpoint="https://idp.example.com/token",
    )

    settings = MagicMock()
    settings.auth.session = session_settings
    settings.auth.web_auth = web_auth
    settings.auth.id_providers = {"test-idp": provider}

    session_data = MagicMock(spec=SessionData)
    session_data.refresh_token = "old-refresh-token"
    session_data.token_expires_at = 0

    session_mgr = MagicMock(spec=SessionManager)
    session_mgr.get_session.return_value = session_data

    with (
        patch.object(SessionManager, "is_token_expired", return_value=True),
        patch(
            "app.dependencies.v1.session.refresh_access_token",
            new_callable=AsyncMock,
            return_value={
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "expires_in": 7200,
            },
        ),
    ):
        result = await get_current_session(
            request=request, settings=settings, session_mgr=session_mgr
        )

    assert result is session_data
    assert session_data.access_token == "new-access-token"
    assert session_data.refresh_token == "new-refresh-token"
    session_mgr.destroy_session.assert_called_once_with("some-session-id")
    session_mgr.create_session.assert_called_once_with(session_data)


@pytest.mark.asyncio
async def test_get_current_session_refresh_failure_returns_none():
    """
    Test that get_current_session returns None when token refresh fails.
    """
    request = MagicMock()
    request.cookies = {"session_id": "some-session-id"}

    session_settings = SessionSettings(session_ttl=3600, cookie_name="session_id")
    web_auth = WebAuthClientSettings(
        provider="test-idp",
        client_id="client-id",
        client_secret="secret",
        redirect_uri="http://localhost/callback",
        scopes=["openid"],
        refresh_enabled=True,
    )
    provider = IDProvider(
        type="jwks",
        issuer_regex=r"^https://idp\.example\.com$",
        jwks_endpoint="https://idp.example.com/jwks",
        token_endpoint="https://idp.example.com/token",
    )

    settings = MagicMock()
    settings.auth.session = session_settings
    settings.auth.web_auth = web_auth
    settings.auth.id_providers = {"test-idp": provider}

    session_data = MagicMock(spec=SessionData)
    session_data.refresh_token = "old-refresh-token"
    session_data.token_expires_at = 0

    session_mgr = MagicMock(spec=SessionManager)
    session_mgr.get_session.return_value = session_data

    with (
        patch.object(SessionManager, "is_token_expired", return_value=True),
        patch(
            "app.dependencies.v1.session.refresh_access_token",
            new_callable=AsyncMock,
            side_effect=Exception("refresh failed"),
        ),
    ):
        result = await get_current_session(
            request=request, settings=settings, session_mgr=session_mgr
        )

    assert result is None


@pytest.mark.asyncio
async def test_get_current_session_refresh_without_new_refresh_token():
    """
    Test token refresh when response does not include a new refresh_token.
    """
    request = MagicMock()
    request.cookies = {"session_id": "some-session-id"}

    session_settings = SessionSettings(session_ttl=3600, cookie_name="session_id")
    web_auth = WebAuthClientSettings(
        provider="test-idp",
        client_id="client-id",
        client_secret="secret",
        redirect_uri="http://localhost/callback",
        scopes=["openid"],
        refresh_enabled=True,
    )
    provider = IDProvider(
        type="jwks",
        issuer_regex=r"^https://idp\.example\.com$",
        jwks_endpoint="https://idp.example.com/jwks",
        token_endpoint="https://idp.example.com/token",
    )

    settings = MagicMock()
    settings.auth.session = session_settings
    settings.auth.web_auth = web_auth
    settings.auth.id_providers = {"test-idp": provider}

    session_data = MagicMock(spec=SessionData)
    session_data.refresh_token = "old-refresh-token"
    session_data.token_expires_at = 0

    session_mgr = MagicMock(spec=SessionManager)
    session_mgr.get_session.return_value = session_data

    with (
        patch.object(SessionManager, "is_token_expired", return_value=True),
        patch(
            "app.dependencies.v1.session.refresh_access_token",
            new_callable=AsyncMock,
            return_value={
                "access_token": "new-access-token",
            },
        ),
    ):
        result = await get_current_session(
            request=request, settings=settings, session_mgr=session_mgr
        )

    assert result is session_data
    assert session_data.access_token == "new-access-token"
    # refresh_token should remain unchanged since response didn't include one
    assert session_data.refresh_token == "old-refresh-token"


@pytest.mark.asyncio
async def test_get_current_session_provider_not_found_skips_refresh():
    """
    Test that get_current_session skips refresh when provider is not found.
    """
    request = MagicMock()
    request.cookies = {"session_id": "some-session-id"}

    session_settings = SessionSettings(session_ttl=3600, cookie_name="session_id")
    web_auth = WebAuthClientSettings(
        provider="missing-idp",
        client_id="client-id",
        client_secret="secret",
        redirect_uri="http://localhost/callback",
        scopes=["openid"],
        refresh_enabled=True,
    )

    settings = MagicMock()
    settings.auth.session = session_settings
    settings.auth.web_auth = web_auth
    settings.auth.id_providers = {}  # provider NOT found

    session_data = MagicMock(spec=SessionData)
    session_data.refresh_token = "old-refresh-token"
    session_data.token_expires_at = 0

    session_mgr = MagicMock(spec=SessionManager)
    session_mgr.get_session.return_value = session_data

    with patch.object(SessionManager, "is_token_expired", return_value=True):
        result = await get_current_session(
            request=request, settings=settings, session_mgr=session_mgr
        )

    # Session is returned without refresh attempt
    assert result is session_data
