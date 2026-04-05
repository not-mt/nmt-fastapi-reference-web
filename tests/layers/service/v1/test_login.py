# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for the login service layer."""

from unittest.mock import MagicMock, patch

import pytest
from nmtfast.auth.v1.acl import AuthSuccess
from nmtfast.auth.v1.exceptions import AuthenticationError
from nmtfast.auth.v1.sessions import SessionManager
from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.settings.v1.schemas import (
    AuthSettings,
    IDProvider,
    SessionSettings,
    WebAuthClientSettings,
)

from app.errors.v1.exceptions import (
    LoginClaimsError,
    LoginCodeExchangeError,
    LoginConfigurationError,
    LoginStateError,
    LoginTokenError,
)
from app.layers.service.v1.login import LoginService


@pytest.fixture
def mock_cache():
    """
    Fixture to provide a mock cache.
    """
    cache = MagicMock(spec=AppCacheBase)
    cache.store_app_cache.return_value = True
    cache.fetch_app_cache.return_value = None
    cache.clear_app_cache.return_value = True
    return cache


@pytest.fixture
def mock_session_mgr(mock_cache):
    """
    Fixture to provide a mock SessionManager.
    """
    session_settings = SessionSettings(session_ttl=3600)
    return SessionManager(mock_cache, session_settings)


@pytest.fixture
def auth_settings_with_web_auth():
    """
    Fixture providing AuthSettings with web_auth and provider configured.
    """
    return AuthSettings(
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
        web_auth=WebAuthClientSettings(
            provider="test-idp",
            client_id="web-client",
            client_secret="secret",
            redirect_uri="http://localhost:8000/callback",
            scopes=["openid"],
            displayname_claims=["name", "preferred_username"],
        ),
        session=SessionSettings(session_ttl=3600),
    )


def test_build_authorization_url_success(auth_settings_with_web_auth, mock_cache):
    """
    Test that build_authorization_url returns a valid URL.
    """
    svc = LoginService(auth_settings_with_web_auth, mock_cache)
    url = svc.build_authorization_url()

    assert "idp.example.com/authorize" in url
    assert "response_type=code" in url
    mock_cache.store_app_cache.assert_called_once()


def test_build_authorization_url_no_web_auth(mock_cache):
    """
    Test that build_authorization_url raises when web_auth is not configured.
    """
    auth = AuthSettings(
        swagger_token_url="https://example.com/token",
        id_providers={},
    )
    svc = LoginService(auth, mock_cache)

    with pytest.raises(LoginConfigurationError):
        svc.build_authorization_url()


def test_build_authorization_url_no_provider(mock_cache):
    """
    Test that build_authorization_url raises when provider is not found.
    """
    auth = AuthSettings(
        swagger_token_url="https://example.com/token",
        id_providers={},
        web_auth=WebAuthClientSettings(
            provider="nonexistent",
            client_id="client",
            client_secret="secret",
            redirect_uri="http://localhost/callback",
            scopes=["openid"],
        ),
    )
    svc = LoginService(auth, mock_cache)

    with pytest.raises(LoginConfigurationError, match="not found"):
        svc.build_authorization_url()


def test_build_authorization_url_with_pkce(mock_cache):
    """
    Test that build_authorization_url handles PKCE when enabled.
    """
    auth = AuthSettings(
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
        web_auth=WebAuthClientSettings(
            provider="test-idp",
            client_id="web-client",
            client_secret="secret",
            redirect_uri="http://localhost/callback",
            scopes=["openid"],
            pkce_enabled=True,
        ),
    )
    svc = LoginService(auth, mock_cache)
    url = svc.build_authorization_url()

    assert "idp.example.com/authorize" in url
    # State data should contain PKCE verifier separated by |
    call_args = mock_cache.store_app_cache.call_args
    assert "|" in call_args.args[1]


@pytest.mark.asyncio
async def test_process_callback_no_web_auth(mock_cache, mock_session_mgr):
    """
    Test that process_callback raises when web_auth is not configured.
    """
    auth = AuthSettings(
        swagger_token_url="https://example.com/token",
        id_providers={},
    )
    svc = LoginService(auth, mock_cache, mock_session_mgr)

    with pytest.raises(LoginConfigurationError):
        await svc.process_callback("code", "state")


@pytest.mark.asyncio
async def test_process_callback_no_session_mgr(auth_settings_with_web_auth, mock_cache):
    """
    Test that process_callback raises when session_mgr is None.
    """
    svc = LoginService(auth_settings_with_web_auth, mock_cache, session_mgr=None)

    with pytest.raises(LoginConfigurationError):
        await svc.process_callback("code", "state")


@pytest.mark.asyncio
async def test_process_callback_invalid_state(
    auth_settings_with_web_auth, mock_cache, mock_session_mgr
):
    """
    Test that process_callback raises on invalid CSRF state.
    """
    mock_cache.fetch_app_cache.return_value = None
    svc = LoginService(auth_settings_with_web_auth, mock_cache, mock_session_mgr)

    with pytest.raises(LoginStateError):
        await svc.process_callback("code", "bad-state")


@pytest.mark.asyncio
async def test_process_callback_provider_not_found(mock_cache, mock_session_mgr):
    """
    Test that process_callback raises when the provider is not found.
    """
    auth = AuthSettings(
        swagger_token_url="https://example.com/token",
        id_providers={},
        web_auth=WebAuthClientSettings(
            provider="nonexistent",
            client_id="client",
            client_secret="secret",
            redirect_uri="http://localhost/callback",
            scopes=["openid"],
        ),
        session=SessionSettings(session_ttl=3600),
    )
    mock_cache.fetch_app_cache.return_value = "valid-state"
    svc = LoginService(auth, mock_cache, mock_session_mgr)

    with pytest.raises(LoginConfigurationError, match="not found"):
        await svc.process_callback("code", "state")


@pytest.mark.asyncio
@patch("app.layers.service.v1.login.exchange_code_for_tokens")
async def test_process_callback_code_exchange_error(
    mock_exchange, auth_settings_with_web_auth, mock_cache, mock_session_mgr
):
    """
    Test that process_callback raises LoginCodeExchangeError on exchange failure.
    """
    mock_cache.fetch_app_cache.return_value = "valid-state"
    mock_exchange.side_effect = AuthenticationError("exchange failed")

    svc = LoginService(auth_settings_with_web_auth, mock_cache, mock_session_mgr)

    with pytest.raises(LoginCodeExchangeError):
        await svc.process_callback("code", "state")


@pytest.mark.asyncio
@patch("app.layers.service.v1.login.authenticate_token")
@patch("app.layers.service.v1.login.exchange_code_for_tokens")
async def test_process_callback_token_validation_error(
    mock_exchange, mock_auth, auth_settings_with_web_auth, mock_cache, mock_session_mgr
):
    """
    Test that process_callback raises LoginTokenError on token validation failure.
    """
    mock_cache.fetch_app_cache.return_value = "valid-state"
    mock_exchange.return_value = {
        "access_token": "at_123",
        "id_token": "header.payload.sig",
        "expires_in": 3600,
    }
    mock_auth.side_effect = Exception("token validation failed")

    svc = LoginService(auth_settings_with_web_auth, mock_cache, mock_session_mgr)

    with pytest.raises(LoginTokenError):
        await svc.process_callback("code", "state")


@pytest.mark.asyncio
@patch("app.layers.service.v1.login.authenticate_token")
@patch("app.layers.service.v1.login.exchange_code_for_tokens")
async def test_process_callback_missing_user_id_claim(
    mock_exchange,
    mock_auth,
    auth_settings_with_web_auth,
    mock_cache,
    mock_session_mgr,
):
    """
    Test that process_callback raises LoginClaimsError when user ID cannot be determined.
    """
    mock_cache.fetch_app_cache.return_value = "valid-state"
    mock_exchange.return_value = {
        "access_token": "at_123",
        # id_token with payload that has NO userid claims (sub, oid, etc.)
        "id_token": "header.eyJpc3MiOiJodHRwczovL2lkcC5leGFtcGxlLmNvbSJ9.sig",
        "expires_in": 3600,
    }
    mock_auth.return_value = AuthSuccess(
        name="web-user",
        acls=[],
    )

    svc = LoginService(auth_settings_with_web_auth, mock_cache, mock_session_mgr)

    with pytest.raises(LoginClaimsError, match="user ID"):
        await svc.process_callback("code", "state")


@pytest.mark.asyncio
@patch("app.layers.service.v1.login.authenticate_token")
@patch("app.layers.service.v1.login.exchange_code_for_tokens")
async def test_process_callback_missing_user_name_claim(
    mock_exchange,
    mock_auth,
    mock_cache,
    mock_session_mgr,
):
    """
    Test that process_callback raises LoginClaimsError when display name is missing.
    """
    auth = AuthSettings(
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
        web_auth=WebAuthClientSettings(
            provider="test-idp",
            client_id="web-client",
            client_secret="secret",
            redirect_uri="http://localhost/callback",
            scopes=["openid"],
            session_claims=["sub"],
            userid_claims=["sub"],
            displayname_claims=["name", "preferred_username"],
        ),
        session=SessionSettings(session_ttl=3600),
    )

    mock_cache.fetch_app_cache.return_value = "valid-state"
    mock_exchange.return_value = {
        "access_token": "at_123",
        # id_token payload has "sub" but NOT "name" or "preferred_username"
        "id_token": "header.eyJzdWIiOiJ1c2VyLTEyMyIsImlzcyI6Imh0dHBzOi8vaWRwLmV4YW1wbGUuY29tIn0.sig",
        "expires_in": 3600,
    }
    mock_auth.return_value = AuthSuccess(name="web-user", acls=[])

    svc = LoginService(auth, mock_cache, mock_session_mgr)

    with pytest.raises(LoginClaimsError, match="display name"):
        await svc.process_callback("code", "state")


@pytest.mark.asyncio
@patch("app.layers.service.v1.login.authenticate_token")
@patch("app.layers.service.v1.login.exchange_code_for_tokens")
async def test_process_callback_success(
    mock_exchange,
    mock_auth,
    auth_settings_with_web_auth,
    mock_cache,
    mock_session_mgr,
):
    """
    Test full successful callback flow.
    """
    mock_cache.fetch_app_cache.return_value = "valid-state"
    mock_exchange.return_value = {
        "access_token": "at_123",
        # payload: {"sub": "user-123", "name": "Test User", "iss": "https://idp.example.com"}
        "id_token": "header.eyJzdWIiOiJ1c2VyLTEyMyIsIm5hbWUiOiJUZXN0IFVzZXIiLCJpc3MiOiJodHRwczovL2lkcC5leGFtcGxlLmNvbSJ9.sig",
        "refresh_token": "rt_456",
        "expires_in": 3600,
    }
    mock_auth.return_value = AuthSuccess(name="web-user", acls=[])

    svc = LoginService(auth_settings_with_web_auth, mock_cache, mock_session_mgr)
    result = await svc.process_callback("auth-code", "valid-state")

    assert result.session_id is not None
    mock_cache.clear_app_cache.assert_called_once()


@pytest.mark.asyncio
@patch("app.layers.service.v1.login.authenticate_token")
@patch("app.layers.service.v1.login.exchange_code_for_tokens")
async def test_process_callback_with_pkce_state(
    mock_exchange,
    mock_auth,
    auth_settings_with_web_auth,
    mock_cache,
    mock_session_mgr,
):
    """
    Test callback flow with PKCE verifier in the cached state.
    """
    mock_cache.fetch_app_cache.return_value = "state-value|pkce-verifier-here"
    mock_exchange.return_value = {
        "access_token": "at_123",
        "id_token": "header.eyJzdWIiOiJ1c2VyLTEyMyIsIm5hbWUiOiJUZXN0IFVzZXIiLCJpc3MiOiJodHRwczovL2lkcC5leGFtcGxlLmNvbSJ9.sig",
        "expires_in": 3600,
    }
    mock_auth.return_value = AuthSuccess(name="web-user", acls=[])

    svc = LoginService(auth_settings_with_web_auth, mock_cache, mock_session_mgr)
    result = await svc.process_callback("auth-code", "valid-state")

    assert result.session_id is not None
    # Verify PKCE verifier was passed to exchange_code_for_tokens
    mock_exchange.assert_awaited_once()
    call_kwargs = mock_exchange.call_args
    assert call_kwargs.kwargs.get("pkce_verifier") == "pkce-verifier-here"


@pytest.mark.asyncio
@patch("app.layers.service.v1.login.authenticate_token")
@patch("app.layers.service.v1.login.exchange_code_for_tokens")
async def test_process_callback_with_bytes_state(
    mock_exchange,
    mock_auth,
    auth_settings_with_web_auth,
    mock_cache,
    mock_session_mgr,
):
    """
    Test callback flow when cached state is bytes instead of string.
    """
    mock_cache.fetch_app_cache.return_value = b"state-value|pkce-verifier"
    mock_exchange.return_value = {
        "access_token": "at_123",
        "id_token": "header.eyJzdWIiOiJ1c2VyLTEyMyIsIm5hbWUiOiJUZXN0IFVzZXIiLCJpc3MiOiJodHRwczovL2lkcC5leGFtcGxlLmNvbSJ9.sig",
        "expires_in": 3600,
    }
    mock_auth.return_value = AuthSuccess(name="web-user", acls=[])

    svc = LoginService(auth_settings_with_web_auth, mock_cache, mock_session_mgr)
    result = await svc.process_callback("auth-code", "valid-state")

    assert result.session_id is not None


@pytest.mark.asyncio
@patch("app.layers.service.v1.login.decode_jwt_part", side_effect=ValueError("bad jwt"))
@patch("app.layers.service.v1.login.authenticate_token")
@patch("app.layers.service.v1.login.exchange_code_for_tokens")
async def test_process_callback_decode_jwt_value_error(
    mock_exchange,
    mock_auth,
    mock_decode,
    auth_settings_with_web_auth,
    mock_cache,
    mock_session_mgr,
):
    """
    Test callback flow when JWT decoding raises ValueError.
    """
    mock_cache.fetch_app_cache.return_value = "valid-state"
    mock_exchange.return_value = {
        "access_token": "at_123",
        "id_token": "header.payload.sig",
        "expires_in": 3600,
    }
    mock_auth.return_value = AuthSuccess(name="web-user", acls=[])

    svc = LoginService(auth_settings_with_web_auth, mock_cache, mock_session_mgr)

    # decode_jwt_part raises ValueError; the code catches it but then
    # user_id will be None and LoginClaimsError is raised
    with pytest.raises(LoginClaimsError, match="user ID"):
        await svc.process_callback("auth-code", "valid-state")


@pytest.mark.asyncio
@patch("app.layers.service.v1.login.authenticate_token")
@patch("app.layers.service.v1.login.exchange_code_for_tokens")
async def test_process_callback_with_dict_state_data(
    mock_exchange,
    mock_auth,
    auth_settings_with_web_auth,
    mock_cache,
    mock_session_mgr,
):
    """
    Test callback flow when cached state data is a dict (non str/bytes).
    """
    mock_cache.fetch_app_cache.return_value = {"state": "some-value"}
    mock_exchange.return_value = {
        "access_token": "at_123",
        "id_token": "header.eyJzdWIiOiJ1c2VyLTEyMyIsIm5hbWUiOiJUZXN0IFVzZXIiLCJpc3MiOiJodHRwczovL2lkcC5leGFtcGxlLmNvbSJ9.sig",
        "expires_in": 3600,
    }
    mock_auth.return_value = AuthSuccess(name="web-user", acls=[])

    svc = LoginService(auth_settings_with_web_auth, mock_cache, mock_session_mgr)
    result = await svc.process_callback("auth-code", "valid-state")

    assert result.session_id is not None
    # PKCE verifier should be None since state data is not str/bytes
    mock_exchange.assert_awaited_once()
    call_kwargs = mock_exchange.call_args
    assert call_kwargs.kwargs.get("pkce_verifier") is None


def test_destroy_session_with_manager(mock_cache, mock_session_mgr):
    """
    Test that destroy_session delegates to session_mgr.
    """
    auth = AuthSettings(
        swagger_token_url="https://example.com/token",
        id_providers={},
    )
    svc = LoginService(auth, mock_cache, mock_session_mgr)
    svc.destroy_session("session-123")

    mock_cache.clear_app_cache.assert_called_once_with("nmt_session_session-123")


def test_destroy_session_without_manager(mock_cache):
    """
    Test that destroy_session does nothing when session_mgr is None.
    """
    auth = AuthSettings(
        swagger_token_url="https://example.com/token",
        id_providers={},
    )
    svc = LoginService(auth, mock_cache, session_mgr=None)
    svc.destroy_session("session-123")
    # Should not raise
