# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Dependencies for server-side session management."""

import logging
from typing import Optional

from fastapi import Depends, Request
from nmtfast.auth.v1.auth_code import refresh_access_token
from nmtfast.auth.v1.sessions import SessionData, SessionManager
from nmtfast.cache.v1.base import AppCacheBase

from app.core.v1.settings import AppSettings, get_app_settings
from app.dependencies.v1.cache import get_cache

logger = logging.getLogger(__name__)


def get_session_manager(
    settings: AppSettings = Depends(get_app_settings),
    cache: AppCacheBase = Depends(get_cache),
) -> Optional[SessionManager]:
    """
    Provide a SessionManager instance if session settings are configured.

    Args:
        settings: The application settings.
        cache: An implementation of AppCacheBase for session storage.

    Returns:
        Optional[SessionManager]: A session manager, or None if sessions are
            not configured.
    """
    if settings.auth.session is None:
        return None
    return SessionManager(cache, settings.auth.session)


async def get_current_session(
    request: Request,
    settings: AppSettings = Depends(get_app_settings),
    session_mgr: Optional[SessionManager] = Depends(get_session_manager),
) -> Optional[SessionData]:
    """
    Extract and validate the current session from the request cookie.

    If refresh tokens are enabled and the access token has expired, an automatic
    refresh is attempted. The refreshed session is stored back in the cache.

    Args:
        request: The incoming HTTP request.
        settings: The application settings.
        session_mgr: The session manager instance (or None if not configured).

    Returns:
        Optional[SessionData]: The session data, or None if no valid session exists.
    """
    if session_mgr is None or settings.auth.session is None:
        return None

    cookie_name = settings.auth.session.cookie_name
    session_id = request.cookies.get(cookie_name)
    if not session_id:
        return None

    session = session_mgr.get_session(session_id)
    if session is None:
        return None

    # attempt token refresh if enabled and token is expired
    if (
        settings.auth.web_auth is not None
        and settings.auth.web_auth.refresh_enabled
        and session.refresh_token
        and SessionManager.is_token_expired(session)
    ):
        provider_name = settings.auth.web_auth.provider
        provider = settings.auth.id_providers.get(provider_name)
        if provider:
            try:
                token_response = await refresh_access_token(
                    provider, settings.auth.web_auth, session.refresh_token
                )
                session.access_token = token_response["access_token"]
                session.token_expires_at = (
                    session.token_expires_at + token_response.get("expires_in", 3600)
                )
                if "refresh_token" in token_response:
                    session.refresh_token = token_response["refresh_token"]

                # update cache
                session_mgr.destroy_session(session_id)
                session_mgr.create_session(session)
                logger.info(f"Refreshed token for session '{session_id}'")
            except Exception:
                logger.warning(f"Token refresh failed for session '{session_id}'")
                return None

    return session
