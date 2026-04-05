# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Business logic for OAuth2 login, callback, and logout flows."""

import logging
import secrets
import time
from typing import Optional

from nmtfast.auth.v1.auth_code import (
    exchange_code_for_tokens,
    generate_authorization_url,
    generate_pkce_pair,
)
from nmtfast.auth.v1.exceptions import AuthenticationError
from nmtfast.auth.v1.jwt import authenticate_token, decode_jwt_part
from nmtfast.auth.v1.sessions import SessionData, SessionManager
from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.settings.v1.schemas import AuthSettings
from pydantic.dataclasses import dataclass

from app.errors.v1.exceptions import (
    LoginClaimsError,
    LoginCodeExchangeError,
    LoginConfigurationError,
    LoginStateError,
    LoginTokenError,
)

logger = logging.getLogger(__name__)

STATE_CACHE_PREFIX = "oauth_state_"
STATE_TTL = 600  # 10 minutes for CSRF state


@dataclass(frozen=True)
class CallbackResult:
    """
    Result of a successful OAuth2 callback.

    Attributes:
        session_id: The newly created session identifier.
    """

    session_id: str


class LoginService:
    """
    Service layer for OAuth2 Authorization Code login, callback, and logout.

    Args:
        auth_settings: The authentication settings.
        cache: An implementation of AppCacheBase for state and session storage.
        session_mgr: The session manager for creating/destroying sessions.
    """

    def __init__(
        self,
        auth_settings: AuthSettings,
        cache: AppCacheBase,
        session_mgr: Optional[SessionManager] = None,
    ) -> None:
        self.auth_settings = auth_settings
        self.cache = cache
        self.session_mgr = session_mgr

    def build_authorization_url(self) -> str:
        """
        Build the IdP authorization URL.

        Generates a CSRF state, optionally a PKCE verifier, caches the state,
        and returns the IdP authorization URL.

        Returns:
            str: The authorization URL to redirect the user to.

        Raises:
            LoginConfigurationError: If web_auth or the provider is not configured.
        """
        web_auth = self.auth_settings.web_auth
        if web_auth is None:
            raise LoginConfigurationError("Web authentication is not configured")

        provider = self.auth_settings.id_providers.get(web_auth.provider)
        if provider is None:
            raise LoginConfigurationError(
                f"Identity provider '{web_auth.provider}' not found in configuration"
            )

        # generate and cache CSRF state
        state = secrets.token_urlsafe(32)
        state_data = state

        # handle PKCE
        pkce_verifier: Optional[str] = None
        if web_auth.pkce_enabled:
            pkce_verifier, _ = generate_pkce_pair()
            state_data = f"{state}|{pkce_verifier}"

        self.cache.store_app_cache(
            f"{STATE_CACHE_PREFIX}{state}", state_data, STATE_TTL
        )

        return generate_authorization_url(
            provider, web_auth, state=state, pkce_verifier=pkce_verifier
        )

    async def process_callback(self, code: str, state: str) -> CallbackResult:
        """
        Process the OAuth2 callback.

        Validates the CSRF state, exchanges the authorization code for tokens,
        validates the JWT, extracts claims, and creates a server-side session.

        Args:
            code: The authorization code from the IdP callback.
            state: The CSRF state parameter from the IdP callback.

        Returns:
            CallbackResult: Contains the new session identifier.

        Raises:
            LoginConfigurationError: If web_auth, session, or provider is missing.
            LoginStateError: If the CSRF state is invalid or expired.
            LoginCodeExchangeError: If the token exchange fails.
            LoginTokenError: If token validation fails.
            LoginClaimsError: If required claims cannot be determined.
        """
        web_auth = self.auth_settings.web_auth
        if web_auth is None or self.session_mgr is None:
            raise LoginConfigurationError("Web authentication is not configured")

        # validate CSRF state
        cached_state_data = self.cache.fetch_app_cache(f"{STATE_CACHE_PREFIX}{state}")
        if cached_state_data is None:
            raise LoginStateError("Invalid or expired state")

        # clear used state immediately
        self.cache.clear_app_cache(f"{STATE_CACHE_PREFIX}{state}")

        # extract PKCE verifier if present
        pkce_verifier: Optional[str] = None
        if isinstance(cached_state_data, (str, bytes)):
            state_str = (
                cached_state_data.decode("utf-8")
                if isinstance(cached_state_data, bytes)
                else cached_state_data
            )
            if "|" in state_str:
                _, pkce_verifier = state_str.split("|", 1)

        provider = self.auth_settings.id_providers.get(web_auth.provider)
        if provider is None:
            raise LoginConfigurationError(
                f"Identity provider '{web_auth.provider}' not found"
            )

        # exchange authorization code for tokens
        try:
            token_response = await exchange_code_for_tokens(
                provider, web_auth, code, pkce_verifier=pkce_verifier
            )
        except AuthenticationError as exc:
            raise LoginCodeExchangeError(f"Token exchange failed: {exc}") from exc

        access_token = token_response.get("access_token", "")
        id_token = token_response.get("id_token", access_token)
        refresh_token = token_response.get("refresh_token")
        expires_in = token_response.get("expires_in", 3600)

        # validate the token and extract ACLs
        try:
            auth_info = await authenticate_token(
                id_token, self.auth_settings, audience=web_auth.client_id
            )
        except Exception as exc:
            raise LoginTokenError(f"Token validation failed: {exc}") from exc

        # extract user claims from the ID token
        user_claims: dict[str, str] = {}
        try:
            payload = decode_jwt_part(id_token, "payload")
            for key in web_auth.session_claims:
                if key in payload:
                    user_claims[key] = str(payload[key])
        except ValueError:
            pass

        user_id: str | None = None
        for claim in web_auth.userid_claims:
            if claim in user_claims:
                user_id = user_claims[claim]
                break

        if not user_id:
            raise LoginClaimsError("Unable to determine user ID from token claims")

        user_name: str | None = None
        for claim in web_auth.displayname_claims:
            if claim in user_claims:
                user_name = user_claims[claim]
                break

        if not user_name:
            raise LoginClaimsError(
                "Unable to determine user display name from token claims"
            )

        # create session
        session_data = SessionData(
            user_id=user_id,
            user_name=user_name,
            user_claims=user_claims,
            acls=auth_info.acls,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=time.time() + expires_in,
            created_at=time.time(),
        )
        session_id = self.session_mgr.create_session(session_data)

        return CallbackResult(session_id=session_id)

    def destroy_session(self, session_id: str) -> None:
        """
        Destroy an existing session.

        Args:
            session_id: The session identifier to destroy.
        """
        if self.session_mgr is not None:
            self.session_mgr.destroy_session(session_id)
