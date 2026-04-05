# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Login, callback, and logout routes for OAuth2 Authorization Code flow."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from nmtfast.auth.v1.sessions import SessionManager
from nmtfast.cache.v1.base import AppCacheBase

from app.core.v1.settings import AppSettings, get_app_settings
from app.dependencies.v1.cache import get_cache
from app.dependencies.v1.session import get_session_manager
from app.errors.v1.exceptions import (
    LoginClaimsError,
    LoginCodeExchangeError,
    LoginConfigurationError,
    LoginStateError,
    LoginTokenError,
)
from app.layers.service.v1.login import LoginService

logger = logging.getLogger(__name__)

login_router = APIRouter(
    prefix="/ui/v1/auth",
    tags=["Web Authentication"],
)


@login_router.get("/login")
async def login(
    request: Request,
    settings: AppSettings = Depends(get_app_settings),
    cache: AppCacheBase = Depends(get_cache),
) -> RedirectResponse:
    """
    Initiate the OAuth2 Authorization Code flow.

    Generates a CSRF state parameter, optionally generates a PKCE verifier,
    and redirects the user to the identity provider's authorization endpoint.

    Args:
        request: The incoming HTTP request.
        settings: The application settings.
        cache: Cache backend for storing CSRF state.

    Returns:
        RedirectResponse: A 302 redirect to the identity provider.

    Raises:
        HTTPException: If web authentication is not configured.
    """
    svc = LoginService(settings.auth, cache)
    try:
        auth_url = svc.build_authorization_url()
    except LoginConfigurationError as exc:
        raise HTTPException(status_code=501, detail=str(exc))

    return RedirectResponse(url=auth_url, status_code=302)


@login_router.get("/callback")
async def callback(
    request: Request,
    settings: AppSettings = Depends(get_app_settings),
    cache: AppCacheBase = Depends(get_cache),
    session_mgr: Optional[SessionManager] = Depends(get_session_manager),
) -> RedirectResponse:
    """
    Handle the OAuth2 callback from the identity provider.

    Validates the CSRF state, exchanges the authorization code for tokens,
    validates the JWT, creates a server-side session, and redirects to the
    web UI.

    Args:
        request: The incoming HTTP request containing code and state parameters.
        settings: The application settings.
        cache: Cache backend for retrieving CSRF state.
        session_mgr: The session manager for creating sessions.

    Returns:
        RedirectResponse: A redirect to the web UI index page.

    Raises:
        HTTPException: If validation or token exchange fails.
    """
    session_settings = settings.auth.session
    if session_settings is None:
        raise HTTPException(
            status_code=501,
            detail="Web authentication is not configured",
        )

    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")

    svc = LoginService(settings.auth, cache, session_mgr)
    try:
        result = await svc.process_callback(code, state)
    except LoginConfigurationError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except LoginStateError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except (LoginCodeExchangeError, LoginTokenError) as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except LoginClaimsError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # set session cookie and redirect
    response = RedirectResponse(url="/ui/v1", status_code=302)
    response.set_cookie(
        key=session_settings.cookie_name,
        value=result.session_id,
        max_age=session_settings.session_ttl,
        path=session_settings.cookie_path,
        secure=session_settings.cookie_secure,
        httponly=session_settings.cookie_httponly,
        samesite=session_settings.cookie_samesite,
    )

    return response


@login_router.get("/logout")
async def logout(
    request: Request,
    settings: AppSettings = Depends(get_app_settings),
    session_mgr: Optional[SessionManager] = Depends(get_session_manager),
) -> RedirectResponse:
    """
    Log out the current user by destroying the session.

    Args:
        request: The incoming HTTP request.
        settings: The application settings.
        session_mgr: The session manager for destroying sessions.

    Returns:
        RedirectResponse: A redirect to the web UI index page.
    """
    session_settings = settings.auth.session

    if session_settings and session_mgr:
        session_id = request.cookies.get(session_settings.cookie_name)
        if session_id:
            svc = LoginService(settings.auth, cache=None, session_mgr=session_mgr)  # type: ignore[arg-type]
            svc.destroy_session(session_id)

    response = RedirectResponse(url="/ui/v1", status_code=302)

    if session_settings:
        response.delete_cookie(
            key=session_settings.cookie_name,
            path=session_settings.cookie_path,
        )

    return response
