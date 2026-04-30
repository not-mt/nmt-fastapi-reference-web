# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""
Widget CRUD web UI router for HTMX-based frontend.

Uses the library's reusable helpers and generic CRUD templates driven
by WIDGET_RESOURCE_CONFIG.
"""

import json
import logging
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, Depends, Form, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from nmtfast.auth.v1.sessions import SessionData
from nmtfast.htmx.v1.helpers import (
    is_htmx,
    login_redirect,
    parse_resource_form_fields,
    render_page,
)
from nmtfast.repositories.widgets.v1.api import WidgetApiRepository
from nmtfast.repositories.widgets.v1.exceptions import WidgetApiException
from nmtfast.repositories.widgets.v1.schemas import (
    WidgetCreate,
    WidgetRead,
    WidgetUpdate,
    WidgetZap,
)

from app.core.v1.resources import NAV_ITEMS, WIDGET_RESOURCE_CONFIG
from app.core.v1.settings import AppSettings
from app.dependencies.v1.api_client import get_api_client
from app.dependencies.v1.preferences import get_user_page_size
from app.dependencies.v1.session import get_current_session
from app.dependencies.v1.settings import get_settings
from app.dependencies.v1.templates import get_templates
from app.layers.service.v1.widgets import WebUIWidgetService

logger = logging.getLogger(__name__)

templates = get_templates()
webui_widgets_router = APIRouter(
    prefix="/ui/v1/widgets",
    tags=["Web UI Widgets"],
)


def get_widget_service(
    api_client: httpx.AsyncClient = Depends(get_api_client),
) -> WebUIWidgetService:
    """
    Provide a WebUIWidgetService using the session-scoped HTTP client.

    Args:
        api_client: The httpx client with the user's Bearer token.

    Returns:
        WebUIWidgetService: Service for widget web UI operations.
    """
    return WebUIWidgetService(WidgetApiRepository(api_client))


@webui_widgets_router.get(
    path="",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def widget_list(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=5000),
    sort_by: str = Query("id"),
    sort_order: Literal["asc", "desc"] = Query("asc", pattern="^(asc|desc)$"),
    search: Optional[str] = Query(None),
    default_page_size: int = Depends(get_user_page_size),
    service: WebUIWidgetService = Depends(get_widget_service),
    session: Optional[SessionData] = Depends(get_current_session),
    settings: AppSettings = Depends(get_settings),
) -> HTMLResponse | RedirectResponse:
    """
    Render the widget list view.

    Args:
        request: The incoming HTTP request.
        page: The page number (1-indexed).
        page_size: The number of items per page (overrides user default).
        sort_by: The field to sort by.
        sort_order: The sort direction ('asc' or 'desc').
        search: Optional search filter string.
        default_page_size: The user's preferred page size from settings.
        service: The widget service.
        session: The current user session, if any.
        settings: The application settings.

    Returns:
        HTMLResponse | RedirectResponse: The widget list or a redirect.
    """
    if session is None:
        return login_redirect(request)

    effective_page_size = page_size if page_size is not None else default_page_size

    try:
        widgets, pagination = await service.list_widgets(
            page=page,
            page_size=effective_page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
        )
    except WidgetApiException:
        widgets = []
        pagination = None

    context = {
        "request": request,
        "session": session,
        "app_name": settings.app_name,
        "items": widgets,
        "pagination": pagination,
        "resource_config": WIDGET_RESOURCE_CONFIG,
        "nav_items": NAV_ITEMS,
    }

    return render_page(
        request,
        templates,
        "v1/partials/crud/list.html",
        context,
    )


@webui_widgets_router.get(
    path="/create",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def widget_create_form(
    request: Request,
    session: Optional[SessionData] = Depends(get_current_session),
) -> HTMLResponse | RedirectResponse:
    """
    Render the widget creation form in the detail panel.

    Args:
        request: The incoming HTTP request.
        session: The current user session, if any.

    Returns:
        HTMLResponse | RedirectResponse: The create form or a redirect.
    """
    if session is None:
        return login_redirect(request)

    return templates.TemplateResponse(
        request,
        "v1/partials/crud/form.html",
        context={
            "request": request,
            "item": None,
            "resource_config": WIDGET_RESOURCE_CONFIG,
            "form_action": "/ui/v1/widgets",
            "form_title": "Create Widget",
        },
    )


@webui_widgets_router.post(
    path="",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_201_CREATED,
)
async def widget_create(
    request: Request,
    name: str = Form(...),
    height: Optional[str] = Form(None),
    mass: Optional[str] = Form(None),
    force: Optional[int] = Form(None),
    service: WebUIWidgetService = Depends(get_widget_service),
    session: Optional[SessionData] = Depends(get_current_session),
    settings: AppSettings = Depends(get_settings),
) -> HTMLResponse | RedirectResponse:
    """
    Handle widget creation form submission.

    Args:
        request: The incoming HTTP request.
        name: The widget name.
        height: The optional height value.
        mass: The optional mass value.
        force: The optional force value.
        service: The widget service.
        session: The current user session, if any.
        settings: The application settings.

    Returns:
        HTMLResponse | RedirectResponse: Updated widget list or a redirect.
    """
    if session is None:
        return login_redirect(request)

    payload = WidgetCreate(name=name, height=height, mass=mass, force=force)

    try:
        await service.create_widget(payload)
    except WidgetApiException as exc:
        logger.warning(f"Failed to create widget: {exc}")

    widgets: list[WidgetRead] = []
    pagination = None
    try:
        widgets, pagination = await service.list_widgets()
    except WidgetApiException:
        pass

    response = templates.TemplateResponse(
        request,
        "v1/partials/crud/list.html",
        context={
            "request": request,
            "session": session,
            "app_name": settings.app_name,
            "items": widgets,
            "pagination": pagination,
            "resource_config": WIDGET_RESOURCE_CONFIG,
            "nav_items": NAV_ITEMS,
        },
    )
    response.headers["HX-Trigger"] = "closeDetailPanel"
    return response


@webui_widgets_router.get(
    path="/{widget_id}",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def widget_detail(
    request: Request,
    widget_id: int,
    service: WebUIWidgetService = Depends(get_widget_service),
    session: Optional[SessionData] = Depends(get_current_session),
    settings: AppSettings = Depends(get_settings),
) -> HTMLResponse | RedirectResponse:
    """
    Render widget detail in the slide-out panel.

    For HTMX requests, returns only the detail partial. For full-page
    requests (deep links), renders the full page with the list in the
    background and the detail panel pre-opened.

    Args:
        request: The incoming HTTP request.
        widget_id: The ID of the widget to display.
        service: The widget service.
        session: The current user session, if any.
        settings: The application settings.

    Returns:
        HTMLResponse | RedirectResponse: The detail panel content or a redirect.
    """
    if session is None:
        return login_redirect(request)

    try:
        widget = await service.get_widget(widget_id)
    except WidgetApiException:
        return HTMLResponse(
            content="<p class='p-6 text-rose-600'>Widget not found.</p>",
            status_code=404,
        )

    if is_htmx(request):
        return templates.TemplateResponse(
            request,
            "v1/partials/crud/detail.html",
            context={
                "request": request,
                "item": widget,
                "resource_config": WIDGET_RESOURCE_CONFIG,
            },
        )

    # Full-page deep link: render list in background with panel pre-opened
    try:
        widgets, pagination = await service.list_widgets()
    except WidgetApiException:
        widgets = []
        pagination = None

    return templates.TemplateResponse(
        request,
        "v1/base.html",
        context={
            "request": request,
            "session": session,
            "app_name": settings.app_name,
            "items": widgets,
            "pagination": pagination,
            "resource_config": WIDGET_RESOURCE_CONFIG,
            "nav_items": NAV_ITEMS,
            "_partial": "v1/partials/crud/list.html",
            "item": widget,
            "panel_partial": "v1/partials/crud/detail.html",
        },
    )


@webui_widgets_router.get(
    path="/{widget_id}/edit",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def widget_edit_form(
    request: Request,
    widget_id: int,
    service: WebUIWidgetService = Depends(get_widget_service),
    session: Optional[SessionData] = Depends(get_current_session),
) -> HTMLResponse | RedirectResponse:
    """
    Render the widget edit form in the detail panel.

    Args:
        request: The incoming HTTP request.
        widget_id: The ID of the widget to edit.
        service: The widget service.
        session: The current user session, if any.

    Returns:
        HTMLResponse | RedirectResponse: The edit form or a redirect.
    """
    if session is None:
        return login_redirect(request)

    try:
        widget = await service.get_widget(widget_id)
    except WidgetApiException:
        return HTMLResponse(
            content="<p class='p-6 text-rose-600'>Widget not found.</p>",
            status_code=404,
        )

    return templates.TemplateResponse(
        request,
        "v1/partials/crud/form.html",
        context={
            "request": request,
            "item": widget,
            "resource_config": WIDGET_RESOURCE_CONFIG,
            "form_action": f"/ui/v1/widgets/{widget_id}",
            "form_title": "Edit Widget",
        },
    )


@webui_widgets_router.patch(
    path="/{widget_id}",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def widget_update(
    request: Request,
    widget_id: int,
    name: str = Form(...),
    height: Optional[str] = Form(None),
    mass: Optional[str] = Form(None),
    force: Optional[int] = Form(None),
    service: WebUIWidgetService = Depends(get_widget_service),
    session: Optional[SessionData] = Depends(get_current_session),
    settings: AppSettings = Depends(get_settings),
) -> HTMLResponse | RedirectResponse:
    """
    Handle widget update form submission.

    Args:
        request: The incoming HTTP request.
        widget_id: The ID of the widget to update.
        name: The widget name.
        height: The optional height value.
        mass: The optional mass value.
        force: The optional force value.
        service: The widget service.
        session: The current user session, if any.
        settings: The application settings.

    Returns:
        HTMLResponse | RedirectResponse: Updated widget list or a redirect.
    """
    if session is None:
        return login_redirect(request)

    payload = WidgetUpdate(name=name, height=height, mass=mass, force=force)

    try:
        await service.update_widget(widget_id, payload)
    except WidgetApiException as exc:
        logger.warning(f"Failed to update widget {widget_id}: {exc}")

    try:
        widget = await service.get_widget(widget_id)
    except WidgetApiException:
        return HTMLResponse(
            content="<p class='p-6 text-rose-600'>Widget not found.</p>",
            status_code=404,
        )

    response = templates.TemplateResponse(
        request,
        "v1/partials/crud/detail.html",
        context={
            "request": request,
            "item": widget,
            "resource_config": WIDGET_RESOURCE_CONFIG,
        },
    )
    response.headers["HX-Trigger"] = "refreshList"
    return response


@webui_widgets_router.delete(
    path="/{widget_id}",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def widget_delete(
    request: Request,
    widget_id: int,
    service: WebUIWidgetService = Depends(get_widget_service),
    session: Optional[SessionData] = Depends(get_current_session),
    settings: AppSettings = Depends(get_settings),
) -> HTMLResponse | RedirectResponse:
    """
    Handle widget deletion.

    On success, returns the refreshed widget list with an HX-Trigger to close
    the modal. On upstream error, returns an error fragment rendered inside the
    delete modal so the user sees the failure immediately.

    Args:
        request: The incoming HTTP request.
        widget_id: The ID of the widget to delete.
        service: The widget service.
        session: The current user session, if any.
        settings: The application settings.

    Returns:
        HTMLResponse | RedirectResponse: Updated widget list on success,
            error detail, or a redirect.
    """
    if session is None:
        return login_redirect(request)

    try:
        await service.delete_widget(widget_id)
    except WidgetApiException as exc:
        logger.warning(f"Failed to delete widget {widget_id}: {exc}")
        return templates.TemplateResponse(
            request,
            "v1/partials/delete_error.html",
            context={
                "request": request,
                "error_status": exc.status_code,
                "error_message": f"The upstream API refused to delete widget {widget_id}.",
            },
        )

    widgets: list[WidgetRead] = []
    pagination = None
    try:
        widgets, pagination = await service.list_widgets()
    except WidgetApiException:
        pass

    response = templates.TemplateResponse(
        request,
        "v1/partials/crud/list.html",
        context={
            "request": request,
            "session": session,
            "app_name": settings.app_name,
            "items": widgets,
            "pagination": pagination,
            "resource_config": WIDGET_RESOURCE_CONFIG,
            "nav_items": NAV_ITEMS,
        },
    )
    response.headers["HX-Retarget"] = "#main-content"
    response.headers["HX-Reswap"] = "innerHTML"
    response.headers["HX-Trigger"] = "deleteSuccess"
    return response


@webui_widgets_router.post(
    path="/actions/bulk/delete",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def widget_bulk_delete(
    request: Request,
    service: WebUIWidgetService = Depends(get_widget_service),
    session: Optional[SessionData] = Depends(get_current_session),
    settings: AppSettings = Depends(get_settings),
) -> HTMLResponse | RedirectResponse:
    """
    Handle bulk widget deletion.

    Reads a JSON body with a list of widget IDs and deletes them.
    Returns the refreshed widget list.

    Args:
        request: The incoming HTTP request.
        service: The widget service.
        session: The current user session, if any.
        settings: The application settings.

    Returns:
        HTMLResponse | RedirectResponse: Updated widget list or a redirect.
    """
    if session is None:
        return login_redirect(request)

    body = await request.json()
    ids: list[int] = [int(i) for i in body.get("ids", [])]

    try:
        await service.bulk_delete_widgets(ids)
    except WidgetApiException as exc:
        logger.warning(f"Failed to bulk delete widgets: {exc}")

    widgets: list[WidgetRead] = []
    pagination = None
    try:
        widgets, pagination = await service.list_widgets()
    except WidgetApiException:
        pass

    response = templates.TemplateResponse(
        request,
        "v1/partials/crud/list.html",
        context={
            "request": request,
            "session": session,
            "app_name": settings.app_name,
            "items": widgets,
            "pagination": pagination,
            "resource_config": WIDGET_RESOURCE_CONFIG,
            "nav_items": NAV_ITEMS,
        },
    )
    response.headers["HX-Retarget"] = "#main-content"
    response.headers["HX-Reswap"] = "innerHTML"
    response.headers["HX-Trigger"] = "deleteSuccess"
    return response


@webui_widgets_router.get(
    path="/actions/bulk/edit",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def widget_bulk_edit_form(
    request: Request,
    ids: str = Query(...),
    session: Optional[SessionData] = Depends(get_current_session),
) -> HTMLResponse | RedirectResponse:
    """
    Render the bulk edit form for multiple widgets.

    Args:
        request: The incoming HTTP request.
        ids: Comma-separated list of widget IDs to edit.
        session: The current user session, if any.

    Returns:
        HTMLResponse | RedirectResponse: The bulk edit form or a redirect.
    """
    if session is None:
        return login_redirect(request)

    id_list: list[str] = [i.strip() for i in ids.split(",") if i.strip()]

    return templates.TemplateResponse(
        request,
        "v1/partials/crud/form.html",
        context={
            "request": request,
            "item": None,
            "resource_config": WIDGET_RESOURCE_CONFIG,
            "form_action": "/ui/v1/widgets/actions/bulk/update",
            "form_title": f"Edit {len(id_list)} Widgets",
            "bulk_edit": True,
            "bulk_ids": id_list,
            "bulk_count": len(id_list),
        },
    )


@webui_widgets_router.post(
    path="/actions/bulk/update",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def widget_bulk_update(
    request: Request,
    service: WebUIWidgetService = Depends(get_widget_service),
    session: Optional[SessionData] = Depends(get_current_session),
    settings: AppSettings = Depends(get_settings),
) -> HTMLResponse | RedirectResponse:
    """
    Handle bulk widget update form submission.

    Parses the form data to determine which fields were submitted (enabled
    via the Apply checkbox) and applies those updates to all selected widgets.

    Args:
        request: The incoming HTTP request.
        service: The widget service.
        session: The current user session, if any.
        settings: The application settings.

    Returns:
        HTMLResponse | RedirectResponse: Updated widget list or a redirect.
    """
    if session is None:
        return login_redirect(request)

    form_data = await request.form()
    ids: list[int] = [int(str(i)) for i in form_data.getlist("ids")]

    update_fields = parse_resource_form_fields(form_data, WIDGET_RESOURCE_CONFIG)

    if update_fields:
        payload = WidgetUpdate(**update_fields)  # type: ignore[arg-type]
        try:
            await service.bulk_update_widgets(ids, payload)
        except WidgetApiException as exc:
            logger.warning(f"Failed to bulk update widgets: {exc}")

    response = HTMLResponse(content="")
    response.headers["HX-Trigger"] = json.dumps(
        {"closeDetailPanel": None, "refreshList": None}
    )
    response.headers["HX-Reswap"] = "none"
    return response


@webui_widgets_router.post(
    path="/{widget_id}/zap",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def widget_zap(
    request: Request,
    widget_id: int,
    duration: int = Form(10),
    service: WebUIWidgetService = Depends(get_widget_service),
    session: Optional[SessionData] = Depends(get_current_session),
) -> HTMLResponse | RedirectResponse:
    """
    Initiate a zap operation on a widget.

    Args:
        request: The incoming HTTP request.
        widget_id: The ID of the widget to zap.
        duration: The zap duration in seconds.
        service: The widget service.
        session: The current user session, if any.

    Returns:
        HTMLResponse | RedirectResponse: The zap status or a redirect.
    """
    if session is None:
        return login_redirect(request)

    try:
        task = await service.zap_widget(widget_id, WidgetZap(duration=duration))
        return templates.TemplateResponse(
            request,
            "v1/partials/crud/zap_status.html",
            context={
                "request": request,
                "item_id": widget_id,
                "task": task,
                "resource_config": WIDGET_RESOURCE_CONFIG,
            },
        )
    except WidgetApiException as exc:
        logger.warning(f"Failed to zap widget {widget_id}: {exc}")
        return HTMLResponse(
            content="<p class='p-4 text-rose-600'>Failed to start zap.</p>",
            status_code=500,
        )


@webui_widgets_router.get(
    path="/{widget_id}/zap/{task_uuid}/status",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def widget_zap_status(
    request: Request,
    widget_id: int,
    task_uuid: str,
    service: WebUIWidgetService = Depends(get_widget_service),
    session: Optional[SessionData] = Depends(get_current_session),
) -> HTMLResponse | RedirectResponse:
    """
    Poll for zap task status.

    Args:
        request: The incoming HTTP request.
        widget_id: The ID of the widget being zapped.
        task_uuid: The UUID of the zap task.
        service: The widget service.
        session: The current user session, if any.

    Returns:
        HTMLResponse | RedirectResponse: Updated task status or a redirect.
    """
    if session is None:
        return login_redirect(request)

    try:
        task = await service.get_zap_status(widget_id, task_uuid)
    except WidgetApiException:
        return HTMLResponse(
            content="<p class='p-4 text-rose-600'>Failed to get status.</p>",
            status_code=500,
        )

    return templates.TemplateResponse(
        request,
        "v1/partials/crud/zap_status.html",
        context={
            "request": request,
            "item_id": widget_id,
            "task": task,
            "resource_config": WIDGET_RESOURCE_CONFIG,
        },
    )
