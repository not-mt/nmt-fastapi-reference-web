# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for login, callback, and logout routes."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from nmtfast.auth.v1.acl import AuthSuccess
from nmtfast.auth.v1.sessions import SessionManager
from nmtfast.settings.v1.schemas import (
    AuthSettings,
    IDProvider,
    IncomingAuthClient,
    IncomingAuthSettings,
    SectionACL,
    SessionSettings,
    WebAuthClientSettings,
)

from app.core.v1.settings import AppSettings, get_app_settings
from app.dependencies.v1.cache import get_cache
from app.dependencies.v1.session import get_session_manager
from app.errors.v1.exceptions import (
    LoginCodeExchangeError,
    LoginConfigurationError,
    LoginTokenError,
)
from app.main import app

client = TestClient(app, follow_redirects=False)


@pytest.fixture
def mock_cache():
    """
    Provide a mock cache backend.
    """
    cache = MagicMock()
    cache.store_app_cache.return_value = True
    cache.fetch_app_cache.return_value = None
    cache.clear_app_cache.return_value = True
    return cache


@pytest.fixture
def web_auth_settings():
    """
    Provide AppSettings with web_auth and session configured.
    """
    settings = MagicMock(spec=AppSettings)
    settings.auth = AuthSettings(
        swagger_token_url="https://idp.example.com/token",
        id_providers={
            "test-idp": IDProvider(
                type="jwks",
                issuer_regex=r"^https://idp\.example\.com$",
                jwks_endpoint="https://idp.example.com/jwks",
                token_endpoint="https://idp.example.com/token",
                authorize_endpoint="https://idp.example.com/authorize",
            ),
        },
        incoming=IncomingAuthSettings(
            clients={
                "web-user": IncomingAuthClient(
                    provider="test-idp",
                    claims={"client_id": "web-client"},
                    acls=[
                        SectionACL(
                            section_regex="^.*$",
                            permissions=["*"],
                        ),
                    ],
                ),
            },
        ),
        web_auth=WebAuthClientSettings(
            provider="test-idp",
            client_id="web-client",
            client_secret="secret",
            redirect_uri="http://localhost:8000/ui/v1/auth/callback",
            scopes=["openid"],
            displayname_claims=["name", "preferred_username"],
        ),
        session=SessionSettings(
            cookie_name="session_id",
            cookie_secure=False,
            cookie_httponly=True,
            cookie_samesite="lax",
            session_ttl=3600,
        ),
    )
    return settings


@pytest.fixture
def mock_session_manager(mock_cache):
    """
    Provide a mock SessionManager.
    """
    session_settings = SessionSettings(session_ttl=3600)
    mgr = SessionManager(mock_cache, session_settings)
    return mgr


def test_login_redirects_to_idp(web_auth_settings, mock_cache):
    """
    Test that GET /ui/v1/auth/login redirects to the IdP authorization endpoint.
    """
    app.dependency_overrides[get_app_settings] = lambda: web_auth_settings
    app.dependency_overrides[get_cache] = lambda: mock_cache

    try:
        response = client.get("/ui/v1/auth/login")
        assert response.status_code == 302
        location = response.headers["location"]
        assert "idp.example.com/authorize" in location
        assert "response_type=code" in location
        assert "client_id=web-client" in location
        assert "state=" in location

        # verify state was cached
        mock_cache.store_app_cache.assert_called_once()
        call_args = mock_cache.store_app_cache.call_args
        assert call_args.args[0].startswith("oauth_state_")
    finally:
        app.dependency_overrides.pop(get_app_settings, None)
        app.dependency_overrides.pop(get_cache, None)


def test_login_returns_501_when_not_configured(mock_cache):
    """
    Test that login returns 501 when web_auth is not configured.
    """
    settings = MagicMock(spec=AppSettings)
    settings.auth = AuthSettings(
        swagger_token_url="https://example.com/token",
        id_providers={},
    )

    app.dependency_overrides[get_app_settings] = lambda: settings
    app.dependency_overrides[get_cache] = lambda: mock_cache

    try:
        response = client.get("/ui/v1/auth/login")
        assert response.status_code == 501
    finally:
        app.dependency_overrides.pop(get_app_settings, None)
        app.dependency_overrides.pop(get_cache, None)


def test_callback_missing_params(web_auth_settings, mock_cache, mock_session_manager):
    """
    Test that callback returns 400 when code or state is missing.
    """
    app.dependency_overrides[get_app_settings] = lambda: web_auth_settings
    app.dependency_overrides[get_cache] = lambda: mock_cache
    app.dependency_overrides[get_session_manager] = lambda: mock_session_manager

    try:
        response = client.get("/ui/v1/auth/callback")
        assert response.status_code == 400

        response = client.get("/ui/v1/auth/callback?code=abc")
        assert response.status_code == 400

        response = client.get("/ui/v1/auth/callback?state=xyz")
        assert response.status_code == 400
    finally:
        app.dependency_overrides.pop(get_app_settings, None)
        app.dependency_overrides.pop(get_cache, None)
        app.dependency_overrides.pop(get_session_manager, None)


def test_callback_invalid_state(web_auth_settings, mock_cache, mock_session_manager):
    """
    Test that callback returns 403 when the state is invalid or expired.
    """
    mock_cache.fetch_app_cache.return_value = None

    app.dependency_overrides[get_app_settings] = lambda: web_auth_settings
    app.dependency_overrides[get_cache] = lambda: mock_cache
    app.dependency_overrides[get_session_manager] = lambda: mock_session_manager

    try:
        response = client.get("/ui/v1/auth/callback?code=abc&state=bad-state")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_app_settings, None)
        app.dependency_overrides.pop(get_cache, None)
        app.dependency_overrides.pop(get_session_manager, None)


@patch("app.layers.service.v1.login.authenticate_token")
@patch("app.layers.service.v1.login.exchange_code_for_tokens")
def test_callback_success(
    mock_exchange, mock_auth_token, web_auth_settings, mock_cache, mock_session_manager
):
    """
    Test the full callback flow: state validation, code exchange, session creation.
    """
    # mock state lookup
    mock_cache.fetch_app_cache.return_value = "valid-state"

    # mock token exchange
    mock_exchange.return_value = {
        "access_token": "at_123",
        "id_token": "header.eyJzdWIiOiJ1c2VyLTEyMyIsIm5hbWUiOiJUZXN0IFVzZXIiLCJpc3MiOiJodHRwczovL2lkcC5leGFtcGxlLmNvbSJ9.sig",
        "expires_in": 3600,
    }

    # mock token validation
    mock_auth_token.return_value = AuthSuccess(
        name="web-user",
        acls=[SectionACL(section_regex="^.*$", permissions=["*"])],
    )

    app.dependency_overrides[get_app_settings] = lambda: web_auth_settings
    app.dependency_overrides[get_cache] = lambda: mock_cache
    app.dependency_overrides[get_session_manager] = lambda: mock_session_manager

    try:
        response = client.get("/ui/v1/auth/callback?code=auth-code&state=valid-state")
        assert response.status_code == 302
        assert response.headers["location"] == "/ui/v1"

        # verify session cookie was set
        set_cookie = response.headers.get("set-cookie", "")
        assert "session_id=" in set_cookie

        # verify state was cleared
        mock_cache.clear_app_cache.assert_called_once()
    finally:
        app.dependency_overrides.pop(get_app_settings, None)
        app.dependency_overrides.pop(get_cache, None)
        app.dependency_overrides.pop(get_session_manager, None)


def test_logout_destroys_session(web_auth_settings, mock_cache, mock_session_manager):
    """
    Test that logout destroys the session and clears the cookie.
    """
    app.dependency_overrides[get_app_settings] = lambda: web_auth_settings
    app.dependency_overrides[get_session_manager] = lambda: mock_session_manager

    try:
        client.cookies.set("session_id", "sess-to-destroy")
        response = client.get("/ui/v1/auth/logout")
        assert response.status_code == 302
        assert response.headers["location"] == "/ui/v1"

        # verify session was destroyed
        mock_cache.clear_app_cache.assert_called_once_with(
            "nmt_session_sess-to-destroy"
        )
    finally:
        client.cookies.clear()
        app.dependency_overrides.pop(get_app_settings, None)
        app.dependency_overrides.pop(get_session_manager, None)


def test_logout_without_session(web_auth_settings, mock_session_manager):
    """
    Test that logout works even without an active session.
    """
    app.dependency_overrides[get_app_settings] = lambda: web_auth_settings
    app.dependency_overrides[get_session_manager] = lambda: mock_session_manager

    try:
        response = client.get("/ui/v1/auth/logout")
        assert response.status_code == 302
    finally:
        app.dependency_overrides.pop(get_app_settings, None)
        app.dependency_overrides.pop(get_session_manager, None)


def test_callback_session_not_configured(mock_cache):
    """
    Test that callback returns 501 when session is not configured.
    """
    settings = MagicMock(spec=AppSettings)
    settings.auth = AuthSettings(
        swagger_token_url="https://example.com/token",
        id_providers={},
    )

    app.dependency_overrides[get_app_settings] = lambda: settings
    app.dependency_overrides[get_cache] = lambda: mock_cache
    app.dependency_overrides[get_session_manager] = lambda: None

    try:
        response = client.get("/ui/v1/auth/callback?code=abc&state=xyz")
        assert response.status_code == 501
    finally:
        app.dependency_overrides.pop(get_app_settings, None)
        app.dependency_overrides.pop(get_cache, None)
        app.dependency_overrides.pop(get_session_manager, None)


@patch("app.layers.service.v1.login.exchange_code_for_tokens")
def test_callback_code_exchange_error(
    mock_exchange, web_auth_settings, mock_cache, mock_session_manager
):
    """
    Test that callback returns 403 when code exchange fails.
    """
    mock_cache.fetch_app_cache.return_value = "valid-state"
    mock_exchange.side_effect = LoginCodeExchangeError("exchange failed")

    app.dependency_overrides[get_app_settings] = lambda: web_auth_settings
    app.dependency_overrides[get_cache] = lambda: mock_cache
    app.dependency_overrides[get_session_manager] = lambda: mock_session_manager

    try:
        response = client.get("/ui/v1/auth/callback?code=abc&state=valid-state")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_app_settings, None)
        app.dependency_overrides.pop(get_cache, None)
        app.dependency_overrides.pop(get_session_manager, None)


@patch("app.layers.service.v1.login.authenticate_token")
@patch("app.layers.service.v1.login.exchange_code_for_tokens")
def test_callback_token_error(
    mock_exchange, mock_auth, web_auth_settings, mock_cache, mock_session_manager
):
    """
    Test that callback returns 403 when token validation fails.
    """
    mock_cache.fetch_app_cache.return_value = "valid-state"
    mock_exchange.return_value = {
        "access_token": "at_123",
        "id_token": "header.payload.sig",
        "expires_in": 3600,
    }
    mock_auth.side_effect = LoginTokenError("token error")

    app.dependency_overrides[get_app_settings] = lambda: web_auth_settings
    app.dependency_overrides[get_cache] = lambda: mock_cache
    app.dependency_overrides[get_session_manager] = lambda: mock_session_manager

    try:
        response = client.get("/ui/v1/auth/callback?code=abc&state=valid-state")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_app_settings, None)
        app.dependency_overrides.pop(get_cache, None)
        app.dependency_overrides.pop(get_session_manager, None)


@patch("app.layers.service.v1.login.authenticate_token")
@patch("app.layers.service.v1.login.exchange_code_for_tokens")
def test_callback_claims_error(
    mock_exchange, mock_auth, web_auth_settings, mock_cache, mock_session_manager
):
    """
    Test that callback returns 500 when claims extraction fails.
    """
    mock_cache.fetch_app_cache.return_value = "valid-state"
    mock_exchange.return_value = {
        "access_token": "at_123",
        "id_token": "header.eyJpc3MiOiJodHRwczovL2lkcC5leGFtcGxlLmNvbSJ9.sig",
        "expires_in": 3600,
    }
    mock_auth.return_value = AuthSuccess(
        name="web-user",
        acls=[SectionACL(section_regex="^.*$", permissions=["*"])],
    )

    app.dependency_overrides[get_app_settings] = lambda: web_auth_settings
    app.dependency_overrides[get_cache] = lambda: mock_cache
    app.dependency_overrides[get_session_manager] = lambda: mock_session_manager

    try:
        response = client.get("/ui/v1/auth/callback?code=abc&state=valid-state")
        assert response.status_code == 500
    finally:
        app.dependency_overrides.pop(get_app_settings, None)
        app.dependency_overrides.pop(get_cache, None)
        app.dependency_overrides.pop(get_session_manager, None)


@patch("app.layers.service.v1.login.LoginService.process_callback")
def test_callback_configuration_error(
    mock_process, web_auth_settings, mock_cache, mock_session_manager
):
    """
    Test that callback returns 501 when LoginConfigurationError is raised.
    """
    mock_process.side_effect = LoginConfigurationError("not configured")

    app.dependency_overrides[get_app_settings] = lambda: web_auth_settings
    app.dependency_overrides[get_cache] = lambda: mock_cache
    app.dependency_overrides[get_session_manager] = lambda: mock_session_manager

    try:
        response = client.get("/ui/v1/auth/callback?code=abc&state=valid-state")
        assert response.status_code == 501
    finally:
        app.dependency_overrides.pop(get_app_settings, None)
        app.dependency_overrides.pop(get_cache, None)
        app.dependency_overrides.pop(get_session_manager, None)


def test_logout_without_session_settings(mock_cache):
    """
    Test that logout works when session settings are None.
    """
    settings = MagicMock(spec=AppSettings)
    settings.auth = AuthSettings(
        swagger_token_url="https://example.com/token",
        id_providers={},
    )

    app.dependency_overrides[get_app_settings] = lambda: settings
    app.dependency_overrides[get_session_manager] = lambda: None

    try:
        response = client.get("/ui/v1/auth/logout")
        assert response.status_code == 302
    finally:
        app.dependency_overrides.pop(get_app_settings, None)
        app.dependency_overrides.pop(get_session_manager, None)
