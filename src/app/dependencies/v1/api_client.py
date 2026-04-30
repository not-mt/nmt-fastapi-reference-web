# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Dependencies for creating API clients that forward the user's session token."""

import logging
from typing import Optional

import httpx
from fastapi import Depends
from nmtfast.auth.v1.sessions import SessionData
from nmtfast.middleware.v1.request_id import REQUEST_ID_CONTEXTVAR

from app.core.v1.settings import AppSettings, get_app_settings
from app.dependencies.v1.session import get_current_session

logger = logging.getLogger(__name__)


def get_api_client(
    settings: AppSettings = Depends(get_app_settings),
    session: Optional[SessionData] = Depends(get_current_session),
) -> httpx.AsyncClient:
    """
    Provide an httpx AsyncClient configured with the user's Bearer token.

    The client points to the reference API base URL and forwards the user's
    access token from the session as a Bearer token (BFF pattern).

    Args:
        settings: The application settings.
        session: The current user session, if any.

    Returns:
        httpx.AsyncClient: An async HTTP client for the reference API.
    """
    headers: dict[str, str] = {}

    if session and session.access_token:
        headers["Authorization"] = f"Bearer {session.access_token}"

    request_id = REQUEST_ID_CONTEXTVAR.get()
    if request_id:
        headers["x-nmtfast-request-id"] = request_id

    return httpx.AsyncClient(
        base_url=settings.upstream.reference_api.url,
        headers=headers,
        timeout=30.0,
    )
