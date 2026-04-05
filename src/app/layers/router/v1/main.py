# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""This module defines endpoints for login, preferences, etc."""

import logging
from typing import Optional

from aiokafka import AIOKafkaProducer
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from nmtfast.auth.v1.sessions import SessionData
from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.settings.v1.schemas import SectionACL
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.v1.settings import AppSettings
from app.dependencies.v1.auth import get_acls
from app.dependencies.v1.cache import get_cache
from app.dependencies.v1.kafka import get_kafka_producer
from app.dependencies.v1.session import get_current_session
from app.dependencies.v1.settings import get_settings
from app.dependencies.v1.sqlalchemy import get_sql_db
from app.layers.service.v1.main import WebUIService

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="src/app/templates")
webui_router = APIRouter(
    prefix="/ui/v1",
    tags=["Web UI Operations"],
    # dependencies=[Depends(authenticate_headers)],
)


# TODO: use specific ACLs for web UI, not API keys / OAuth tokens
def get_webui_service(
    db: AsyncSession = Depends(get_sql_db),
    acls: list[SectionACL] = Depends(get_acls),
    settings: AppSettings = Depends(get_settings),
    cache: AppCacheBase = Depends(get_cache),
    kafka: Optional[AIOKafkaProducer] = Depends(get_kafka_producer),
) -> WebUIService:
    """
    Dependency function to provide a WebUIService instance.

    Args:
        db: The asynchronous database session.
        acls: List of ACLs associated with authenticated client/apikey.
        settings: The application's AppSettings object.
        cache: An implementation of AppCacheBase, used for getting/setting cache data.
        kafka: Optional Kafka producer, if enabled in configuration.

    Returns:
        WebUIService: An instance of the WebUIService.
    """
    return WebUIService(acls, settings, cache, kafka)


@webui_router.get(
    path="",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def get_index(
    request: Request,
    webui_service: WebUIService = Depends(get_webui_service),
    session: Optional[SessionData] = Depends(get_current_session),
    settings: AppSettings = Depends(get_settings),
) -> HTMLResponse | RedirectResponse:
    """
    Render the main index page.

    Redirects unauthenticated users to the login page.

    Args:
        request: The incoming HTTP request.
        webui_service: The web UI service layer.
        session: The current user session, if any.
        settings: The application settings.

    Returns:
        HTMLResponse | RedirectResponse: The rendered page or a redirect to login.
    """
    if session is None:
        return RedirectResponse(url="/ui/v1/login", status_code=302)

    await webui_service.dummy_index()

    return templates.TemplateResponse(
        request,
        "v1/index.html",
        context={
            "request": request,
            "session": session,
            "app_name": settings.app_name,
        },
    )


@webui_router.get(
    path="/login",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def get_login_page(
    request: Request,
    session: Optional[SessionData] = Depends(get_current_session),
    settings: AppSettings = Depends(get_settings),
) -> HTMLResponse | RedirectResponse:
    """
    Render the login page.

    Redirects authenticated users to the index page.

    Args:
        request: The incoming HTTP request.
        session: The current user session, if any.
        settings: The application settings.

    Returns:
        HTMLResponse | RedirectResponse: The login page or a redirect to index.
    """
    if session is not None:
        return RedirectResponse(url="/ui/v1", status_code=302)

    return templates.TemplateResponse(
        request,
        "v1/login.html",
        context={
            "request": request,
            "app_name": settings.app_name,
            "error": request.query_params.get("error"),
        },
    )
