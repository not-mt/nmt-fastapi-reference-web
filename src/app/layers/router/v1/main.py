# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""This module defines endpoints for login, preferences, etc."""

import logging
from typing import Optional

import httpx
from aiokafka import AIOKafkaProducer
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from nmtfast.auth.v1.sessions import SessionData
from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.htmx.v1.helpers import is_htmx, login_redirect, render_page
from nmtfast.repositories.gadgets.v1.api import GadgetApiRepository
from nmtfast.repositories.widgets.v1.api import WidgetApiRepository
from nmtfast.settings.v1.schemas import SectionACL
from pymongo.asynchronous.database import AsyncDatabase as AsyncMongoDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.v1.resources import NAV_ITEMS, SETTINGS_SECTIONS
from app.core.v1.settings import AppSettings
from app.dependencies.v1.api_client import get_api_client
from app.dependencies.v1.auth import get_acls
from app.dependencies.v1.cache import get_cache
from app.dependencies.v1.kafka import get_kafka_producer
from app.dependencies.v1.mongo import get_mongo_db
from app.dependencies.v1.session import get_current_session
from app.dependencies.v1.settings import get_settings
from app.dependencies.v1.sqlalchemy import get_sql_db
from app.dependencies.v1.templates import get_templates
from app.layers.repository.v1.user_settings import UserSettingRepository
from app.layers.service.v1.gadgets import WebUIGadgetService
from app.layers.service.v1.main import WebUIService
from app.layers.service.v1.web_user_settings import WebUIUserSettingsService
from app.layers.service.v1.widgets import WebUIWidgetService

logger = logging.getLogger(__name__)

COMMON_TIMEZONES: list[str] = [
    "UTC",
    "US/Eastern",
    "US/Central",
    "US/Mountain",
    "US/Pacific",
    "US/Alaska",
    "US/Hawaii",
    "Canada/Atlantic",
    "Canada/Eastern",
    "Canada/Central",
    "Canada/Mountain",
    "Canada/Pacific",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Moscow",
    "Asia/Tokyo",
    "Asia/Shanghai",
    "Asia/Kolkata",
    "Asia/Dubai",
    "Australia/Sydney",
    "Australia/Melbourne",
    "Pacific/Auckland",
]

templates = get_templates()
webui_router = APIRouter(
    prefix="/ui/v1",
    tags=["Web UI Operations"],
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


async def _fetch_dashboard_counts(
    api_client: httpx.AsyncClient,
) -> tuple[int | None, int | None]:
    """
    Fetch total widget and gadget counts from the upstream API.

    Uses page_size=1 to minimise data transfer. Returns None for either
    value when the upstream API is unreachable or returns an error.

    Args:
        api_client: The httpx client with the user's Bearer token.

    Returns:
        tuple[int | None, int | None]: Widget count and gadget count,
            or None for each if the API call fails.
    """
    widget_count: int | None = None
    gadget_count: int | None = None

    try:
        widget_svc = WebUIWidgetService(WidgetApiRepository(api_client))
        _, w_meta = await widget_svc.list_widgets(page=1, page_size=1)
        widget_count = w_meta.total
    except Exception:
        logger.warning("Failed to fetch widget count for dashboard")

    try:
        gadget_svc = WebUIGadgetService(GadgetApiRepository(api_client))
        _, g_meta = await gadget_svc.list_gadgets(page=1, page_size=1)
        gadget_count = g_meta.total
    except Exception:
        logger.warning("Failed to fetch gadget count for dashboard")

    return widget_count, gadget_count


async def _fetch_display_name(db: AsyncMongoDatabase, user_id: str) -> str:
    """
    Retrieve the user's display name preference from MongoDB.

    Args:
        db: The asynchronous MongoDB database.
        user_id: The ID of the user.

    Returns:
        str: The display name, or an empty string if not set.
    """
    try:
        repo = UserSettingRepository(db)
        setting = await repo.get_by_user_and_name(user_id, "display_name")
        return setting.value if setting else ""
    except Exception:
        logger.warning("Failed to fetch display name for dashboard")
        return ""


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
    api_client: httpx.AsyncClient = Depends(get_api_client),
    db: AsyncMongoDatabase = Depends(get_mongo_db),
) -> HTMLResponse | RedirectResponse:
    """
    Render the main index page.

    Redirects unauthenticated users to the login page.

    Args:
        request: The incoming HTTP request.
        webui_service: The web UI service layer.
        session: The current user session, if any.
        settings: The application settings.
        api_client: The httpx client with the user's Bearer token.
        db: The asynchronous MongoDB database.

    Returns:
        HTMLResponse | RedirectResponse: The rendered page or a redirect to login.
    """
    if session is None:
        return login_redirect(request)

    await webui_service.dummy_index()

    widget_count, gadget_count = await _fetch_dashboard_counts(api_client)
    display_name = await _fetch_display_name(db, session.user_id)

    return templates.TemplateResponse(
        request,
        "v1/index.html",
        context={
            "request": request,
            "session": session,
            "app_name": settings.app_name,
            "nav_items": NAV_ITEMS,
            "widget_count": widget_count,
            "gadget_count": gadget_count,
            "display_name": display_name,
        },
    )


@webui_router.get(
    path="/delete-confirm",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def get_delete_confirm(
    request: Request,
    delete_url: str,
    resource_type: str,
    resource_name: str,
    session: Optional[SessionData] = Depends(get_current_session),
) -> HTMLResponse | RedirectResponse:
    """
    Render the delete confirmation modal content.

    Args:
        request: The incoming HTTP request.
        delete_url: The URL to issue the DELETE request against.
        resource_type: The type of resource being deleted (e.g. "Widget").
        resource_name: The display name of the resource.
        session: The current user session, if any.

    Returns:
        HTMLResponse | RedirectResponse: The confirmation partial or a redirect.
    """
    if session is None:
        return login_redirect(request)

    if not delete_url.startswith("/ui/v1/"):
        return HTMLResponse(content="Invalid delete URL", status_code=400)

    return templates.TemplateResponse(
        request,
        "v1/partials/delete_confirm.html",
        context={
            "request": request,
            "delete_url": delete_url,
            "resource_type": resource_type,
            "resource_name": resource_name,
        },
    )


@webui_router.get(
    path="/dashboard",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def get_dashboard(
    request: Request,
    session: Optional[SessionData] = Depends(get_current_session),
    settings: AppSettings = Depends(get_settings),
    api_client: httpx.AsyncClient = Depends(get_api_client),
    db: AsyncMongoDatabase = Depends(get_mongo_db),
) -> HTMLResponse | RedirectResponse:
    """
    Render the dashboard page or partial.

    Args:
        request: The incoming HTTP request.
        session: The current user session, if any.
        settings: The application settings.
        api_client: The httpx client with the user's Bearer token.
        db: The asynchronous MongoDB database.

    Returns:
        HTMLResponse | RedirectResponse: The dashboard content or a redirect.
    """
    if session is None:
        return login_redirect(request)

    widget_count, gadget_count = await _fetch_dashboard_counts(api_client)
    display_name = await _fetch_display_name(db, session.user_id)

    context = {
        "request": request,
        "session": session,
        "app_name": settings.app_name,
        "nav_items": NAV_ITEMS,
        "widget_count": widget_count,
        "gadget_count": gadget_count,
        "display_name": display_name,
    }

    if is_htmx(request):
        return templates.TemplateResponse(
            request,
            "v1/partials/dashboard.html",
            context=context,
        )

    return templates.TemplateResponse(
        request,
        "v1/index.html",
        context=context,
    )


@webui_router.get(
    path="/profile",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def get_profile(
    request: Request,
    session: Optional[SessionData] = Depends(get_current_session),
    settings: AppSettings = Depends(get_settings),
) -> HTMLResponse | RedirectResponse:
    """
    Render the profile page showing session claims and ACLs.

    Args:
        request: The incoming HTTP request.
        session: The current user session, if any.
        settings: The application settings.

    Returns:
        HTMLResponse | RedirectResponse: The profile content or a redirect.
    """
    if session is None:
        return login_redirect(request)

    context = {
        "request": request,
        "session": session,
        "app_name": settings.app_name,
        "nav_items": NAV_ITEMS,
    }

    return render_page(request, templates, "v1/partials/profile.html", context)


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


# ── Settings ──


def get_web_user_settings_service(
    db: AsyncMongoDatabase = Depends(get_mongo_db),
) -> WebUIUserSettingsService:
    """
    Dependency function to provide a WebUIUserSettingsService instance.

    Args:
        db: The asynchronous MongoDB database.

    Returns:
        WebUIUserSettingsService: An instance of the service.
    """
    repo = UserSettingRepository(db)
    return WebUIUserSettingsService(repo)


@webui_router.get(
    path="/settings",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def get_settings_modal(
    request: Request,
    session: Optional[SessionData] = Depends(get_current_session),
    svc: WebUIUserSettingsService = Depends(get_web_user_settings_service),
) -> HTMLResponse | RedirectResponse:
    """
    Render the settings modal shell with the General section pre-loaded.

    Args:
        request: The incoming HTTP request.
        session: The current user session, if any.
        svc: The web user settings service.

    Returns:
        HTMLResponse | RedirectResponse: The settings modal content or
            a redirect to login.
    """
    if session is None:
        return login_redirect(request)

    preferences = await svc.get_preferences(session.user_id)

    return templates.TemplateResponse(
        request,
        "v1/partials/settings_modal.html",
        context={
            "request": request,
            "settings_sections": SETTINGS_SECTIONS,
            "preferences": preferences,
            "timezones": COMMON_TIMEZONES,
            "success_message": None,
            "error_message": None,
            "_settings_partial": "v1/partials/settings/general.html",
        },
    )


@webui_router.get(
    path="/settings/general",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def get_settings_general(
    request: Request,
    session: Optional[SessionData] = Depends(get_current_session),
    svc: WebUIUserSettingsService = Depends(get_web_user_settings_service),
) -> HTMLResponse | RedirectResponse:
    """
    Render the General settings section partial.

    Args:
        request: The incoming HTTP request.
        session: The current user session, if any.
        svc: The web user settings service.

    Returns:
        HTMLResponse | RedirectResponse: The General settings partial or
            a redirect to login.
    """
    if session is None:
        return login_redirect(request)

    preferences = await svc.get_preferences(session.user_id)

    return templates.TemplateResponse(
        request,
        "v1/partials/settings/general.html",
        context={
            "request": request,
            "preferences": preferences,
            "timezones": COMMON_TIMEZONES,
            "success_message": None,
            "error_message": None,
        },
    )


@webui_router.post(
    path="/settings/general",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def post_settings_general(
    request: Request,
    display_name: str = Form(""),
    timezone: str = Form(""),
    page_size: int = Form(10),
    session: Optional[SessionData] = Depends(get_current_session),
    svc: WebUIUserSettingsService = Depends(get_web_user_settings_service),
) -> HTMLResponse | RedirectResponse:
    """
    Save the General settings and re-render the section partial.

    Args:
        request: The incoming HTTP request.
        display_name: The display name from the form.
        timezone: The timezone from the form.
        page_size: The preferred items per page from the form.
        session: The current user session, if any.
        svc: The web user settings service.

    Returns:
        HTMLResponse | RedirectResponse: The updated General settings
            partial or a redirect to login.
    """
    if session is None:
        return login_redirect(request)

    preferences = await svc.update_preferences(
        session.user_id, display_name, timezone, page_size
    )

    return templates.TemplateResponse(
        request,
        "v1/partials/settings/general.html",
        context={
            "request": request,
            "preferences": preferences,
            "timezones": COMMON_TIMEZONES,
            "success_message": "Settings saved successfully.",
            "error_message": None,
        },
    )
