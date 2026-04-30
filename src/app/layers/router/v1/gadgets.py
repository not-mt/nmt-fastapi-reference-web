# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""
Gadget CRUD web UI router for HTMX-based frontend.

Uses the library's reusable helpers and generic CRUD templates driven
by GADGET_RESOURCE_CONFIG.
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
from nmtfast.repositories.gadgets.v1.api import GadgetApiRepository
from nmtfast.repositories.gadgets.v1.exceptions import GadgetApiException
from nmtfast.repositories.gadgets.v1.schemas import (
    GadgetCreate,
    GadgetRead,
    GadgetUpdate,
    GadgetZap,
)

from app.core.v1.resources import GADGET_RESOURCE_CONFIG, NAV_ITEMS
from app.core.v1.settings import AppSettings
from app.dependencies.v1.api_client import get_api_client
from app.dependencies.v1.preferences import get_user_page_size
from app.dependencies.v1.session import get_current_session
from app.dependencies.v1.settings import get_settings
from app.dependencies.v1.templates import get_templates
from app.layers.service.v1.gadgets import WebUIGadgetService

logger = logging.getLogger(__name__)

templates = get_templates()
webui_gadgets_router = APIRouter(
    prefix="/ui/v1/gadgets",
    tags=["Web UI Gadgets"],
)


def get_gadget_service(
    api_client: httpx.AsyncClient = Depends(get_api_client),
) -> WebUIGadgetService:
    """
    Provide a WebUIGadgetService using the session-scoped HTTP client.

    Args:
        api_client: The httpx client with the user's Bearer token.

    Returns:
        WebUIGadgetService: Service for gadget web UI operations.
    """
    return WebUIGadgetService(GadgetApiRepository(api_client))


@webui_gadgets_router.get(
    path="",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def gadget_list(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=5000),
    sort_by: str = Query("id"),
    sort_order: Literal["asc", "desc"] = Query("asc", pattern="^(asc|desc)$"),
    search: Optional[str] = Query(None),
    default_page_size: int = Depends(get_user_page_size),
    service: WebUIGadgetService = Depends(get_gadget_service),
    session: Optional[SessionData] = Depends(get_current_session),
    settings: AppSettings = Depends(get_settings),
) -> HTMLResponse | RedirectResponse:
    """
    Render the gadget list view.

    Args:
        request: The incoming HTTP request.
        page: The page number (1-indexed).
        page_size: The number of items per page (overrides user default).
        sort_by: The field to sort by.
        sort_order: The sort direction ('asc' or 'desc').
        search: Optional search filter string.
        default_page_size: The user's preferred page size from settings.
        service: The gadget service.
        session: The current user session, if any.
        settings: The application settings.

    Returns:
        HTMLResponse | RedirectResponse: The gadget list or a redirect.
    """
    if session is None:
        return login_redirect(request)

    effective_page_size = page_size if page_size is not None else default_page_size

    try:
        gadgets, pagination = await service.list_gadgets(
            page=page,
            page_size=effective_page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
        )
    except GadgetApiException:
        gadgets = []
        pagination = None

    context = {
        "request": request,
        "session": session,
        "app_name": settings.app_name,
        "items": gadgets,
        "pagination": pagination,
        "resource_config": GADGET_RESOURCE_CONFIG,
        "nav_items": NAV_ITEMS,
    }

    return render_page(
        request,
        templates,
        "v1/partials/crud/list.html",
        context,
    )


@webui_gadgets_router.get(
    path="/create",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def gadget_create_form(
    request: Request,
    session: Optional[SessionData] = Depends(get_current_session),
) -> HTMLResponse | RedirectResponse:
    """
    Render the gadget creation form in the detail panel.

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
            "resource_config": GADGET_RESOURCE_CONFIG,
            "form_action": "/ui/v1/gadgets",
            "form_title": "Create Gadget",
        },
    )


@webui_gadgets_router.post(
    path="",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_201_CREATED,
)
async def gadget_create(
    request: Request,
    name: str = Form(...),
    height: Optional[str] = Form(None),
    mass: Optional[str] = Form(None),
    force: Optional[int] = Form(None),
    service: WebUIGadgetService = Depends(get_gadget_service),
    session: Optional[SessionData] = Depends(get_current_session),
    settings: AppSettings = Depends(get_settings),
) -> HTMLResponse | RedirectResponse:
    """
    Handle gadget creation form submission.

    Args:
        request: The incoming HTTP request.
        name: The gadget name.
        height: The optional height value.
        mass: The optional mass value.
        force: The optional force value.
        service: The gadget service.
        session: The current user session, if any.
        settings: The application settings.

    Returns:
        HTMLResponse | RedirectResponse: Updated gadget list or a redirect.
    """
    if session is None:
        return login_redirect(request)

    payload = GadgetCreate(name=name, height=height, mass=mass, force=force)

    try:
        await service.create_gadget(payload)
    except GadgetApiException as exc:
        logger.warning(f"Failed to create gadget: {exc}")

    gadgets: list[GadgetRead] = []
    pagination = None
    try:
        gadgets, pagination = await service.list_gadgets()
    except GadgetApiException:
        pass

    response = templates.TemplateResponse(
        request,
        "v1/partials/crud/list.html",
        context={
            "request": request,
            "session": session,
            "app_name": settings.app_name,
            "items": gadgets,
            "pagination": pagination,
            "resource_config": GADGET_RESOURCE_CONFIG,
            "nav_items": NAV_ITEMS,
        },
    )
    response.headers["HX-Trigger"] = "closeDetailPanel"
    return response


@webui_gadgets_router.get(
    path="/{gadget_id}",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def gadget_detail(
    request: Request,
    gadget_id: str,
    service: WebUIGadgetService = Depends(get_gadget_service),
    session: Optional[SessionData] = Depends(get_current_session),
    settings: AppSettings = Depends(get_settings),
) -> HTMLResponse | RedirectResponse:
    """
    Render gadget detail in the slide-out panel.

    For HTMX requests, returns only the detail partial. For full-page
    requests (deep links), renders the full page with the list in the
    background and the detail panel pre-opened.

    Args:
        request: The incoming HTTP request.
        gadget_id: The ID of the gadget to display.
        service: The gadget service.
        session: The current user session, if any.
        settings: The application settings.

    Returns:
        HTMLResponse | RedirectResponse: The detail panel content or a redirect.
    """
    if session is None:
        return login_redirect(request)

    try:
        gadget = await service.get_gadget(gadget_id)
    except GadgetApiException:
        return HTMLResponse(
            content="<p class='p-6 text-rose-600'>Gadget not found.</p>",
            status_code=404,
        )

    if is_htmx(request):
        return templates.TemplateResponse(
            request,
            "v1/partials/crud/detail.html",
            context={
                "request": request,
                "item": gadget,
                "resource_config": GADGET_RESOURCE_CONFIG,
            },
        )

    # Full-page deep link: render list in background with panel pre-opened
    try:
        gadgets, pagination = await service.list_gadgets()
    except GadgetApiException:
        gadgets = []
        pagination = None

    return templates.TemplateResponse(
        request,
        "v1/base.html",
        context={
            "request": request,
            "session": session,
            "app_name": settings.app_name,
            "items": gadgets,
            "pagination": pagination,
            "resource_config": GADGET_RESOURCE_CONFIG,
            "nav_items": NAV_ITEMS,
            "_partial": "v1/partials/crud/list.html",
            "item": gadget,
            "panel_partial": "v1/partials/crud/detail.html",
        },
    )


@webui_gadgets_router.get(
    path="/{gadget_id}/edit",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def gadget_edit_form(
    request: Request,
    gadget_id: str,
    service: WebUIGadgetService = Depends(get_gadget_service),
    session: Optional[SessionData] = Depends(get_current_session),
) -> HTMLResponse | RedirectResponse:
    """
    Render the gadget edit form in the detail panel.

    Args:
        request: The incoming HTTP request.
        gadget_id: The ID of the gadget to edit.
        service: The gadget service.
        session: The current user session, if any.

    Returns:
        HTMLResponse | RedirectResponse: The edit form or a redirect.
    """
    if session is None:
        return login_redirect(request)

    try:
        gadget = await service.get_gadget(gadget_id)
    except GadgetApiException:
        return HTMLResponse(
            content="<p class='p-6 text-rose-600'>Gadget not found.</p>",
            status_code=404,
        )

    return templates.TemplateResponse(
        request,
        "v1/partials/crud/form.html",
        context={
            "request": request,
            "item": gadget,
            "resource_config": GADGET_RESOURCE_CONFIG,
            "form_action": f"/ui/v1/gadgets/{gadget_id}",
            "form_title": "Edit Gadget",
        },
    )


@webui_gadgets_router.patch(
    path="/{gadget_id}",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def gadget_update(
    request: Request,
    gadget_id: str,
    name: str = Form(...),
    height: Optional[str] = Form(None),
    mass: Optional[str] = Form(None),
    force: Optional[int] = Form(None),
    service: WebUIGadgetService = Depends(get_gadget_service),
    session: Optional[SessionData] = Depends(get_current_session),
    settings: AppSettings = Depends(get_settings),
) -> HTMLResponse | RedirectResponse:
    """
    Handle gadget update form submission.

    Args:
        request: The incoming HTTP request.
        gadget_id: The ID of the gadget to update.
        name: The gadget name.
        height: The optional height value.
        mass: The optional mass value.
        force: The optional force value.
        service: The gadget service.
        session: The current user session, if any.
        settings: The application settings.

    Returns:
        HTMLResponse | RedirectResponse: Updated gadget list or a redirect.
    """
    if session is None:
        return login_redirect(request)

    payload = GadgetUpdate(name=name, height=height, mass=mass, force=force)

    try:
        await service.update_gadget(gadget_id, payload)
    except GadgetApiException as exc:
        logger.warning(f"Failed to update gadget {gadget_id}: {exc}")

    try:
        gadget = await service.get_gadget(gadget_id)
    except GadgetApiException:
        return HTMLResponse(
            content="<p class='p-6 text-rose-600'>Gadget not found.</p>",
            status_code=404,
        )

    response = templates.TemplateResponse(
        request,
        "v1/partials/crud/detail.html",
        context={
            "request": request,
            "item": gadget,
            "resource_config": GADGET_RESOURCE_CONFIG,
        },
    )
    response.headers["HX-Trigger"] = "refreshList"
    return response


@webui_gadgets_router.delete(
    path="/{gadget_id}",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def gadget_delete(
    request: Request,
    gadget_id: str,
    service: WebUIGadgetService = Depends(get_gadget_service),
    session: Optional[SessionData] = Depends(get_current_session),
    settings: AppSettings = Depends(get_settings),
) -> HTMLResponse | RedirectResponse:
    """
    Handle gadget deletion.

    On success, returns the refreshed gadget list with an HX-Trigger to close
    the modal. On upstream error, returns an error fragment rendered inside the
    delete modal so the user sees the failure immediately.

    Args:
        request: The incoming HTTP request.
        gadget_id: The ID of the gadget to delete.
        service: The gadget service.
        session: The current user session, if any.
        settings: The application settings.

    Returns:
        HTMLResponse | RedirectResponse: Updated gadget list on success,
            error detail, or a redirect.
    """
    if session is None:
        return login_redirect(request)

    try:
        await service.delete_gadget(gadget_id)
    except GadgetApiException as exc:
        logger.warning(f"Failed to delete gadget {gadget_id}: {exc}")
        return templates.TemplateResponse(
            request,
            "v1/partials/delete_error.html",
            context={
                "request": request,
                "error_status": exc.status_code,
                "error_message": f"The upstream API refused to delete gadget {gadget_id}.",
            },
        )

    gadgets: list[GadgetRead] = []
    pagination = None
    try:
        gadgets, pagination = await service.list_gadgets()
    except GadgetApiException:
        pass

    response = templates.TemplateResponse(
        request,
        "v1/partials/crud/list.html",
        context={
            "request": request,
            "session": session,
            "app_name": settings.app_name,
            "items": gadgets,
            "pagination": pagination,
            "resource_config": GADGET_RESOURCE_CONFIG,
            "nav_items": NAV_ITEMS,
        },
    )
    response.headers["HX-Retarget"] = "#main-content"
    response.headers["HX-Reswap"] = "innerHTML"
    response.headers["HX-Trigger"] = "deleteSuccess"
    return response


@webui_gadgets_router.post(
    path="/actions/bulk/delete",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def gadget_bulk_delete(
    request: Request,
    service: WebUIGadgetService = Depends(get_gadget_service),
    session: Optional[SessionData] = Depends(get_current_session),
    settings: AppSettings = Depends(get_settings),
) -> HTMLResponse | RedirectResponse:
    """
    Handle bulk gadget deletion.

    Reads a JSON body with a list of gadget IDs and deletes them.
    Returns the refreshed gadget list.

    Args:
        request: The incoming HTTP request.
        service: The gadget service.
        session: The current user session, if any.
        settings: The application settings.

    Returns:
        HTMLResponse | RedirectResponse: Updated gadget list or a redirect.
    """
    if session is None:
        return login_redirect(request)

    body = await request.json()
    ids: list[str] = [str(i) for i in body.get("ids", [])]

    try:
        await service.bulk_delete_gadgets(ids)
    except GadgetApiException as exc:
        logger.warning(f"Failed to bulk delete gadgets: {exc}")

    gadgets: list[GadgetRead] = []
    pagination = None
    try:
        gadgets, pagination = await service.list_gadgets()
    except GadgetApiException:
        pass

    response = templates.TemplateResponse(
        request,
        "v1/partials/crud/list.html",
        context={
            "request": request,
            "session": session,
            "app_name": settings.app_name,
            "items": gadgets,
            "pagination": pagination,
            "resource_config": GADGET_RESOURCE_CONFIG,
            "nav_items": NAV_ITEMS,
        },
    )
    response.headers["HX-Retarget"] = "#main-content"
    response.headers["HX-Reswap"] = "innerHTML"
    response.headers["HX-Trigger"] = "deleteSuccess"
    return response


@webui_gadgets_router.get(
    path="/actions/bulk/edit",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def gadget_bulk_edit_form(
    request: Request,
    ids: str = Query(...),
    session: Optional[SessionData] = Depends(get_current_session),
) -> HTMLResponse | RedirectResponse:
    """
    Render the bulk edit form for multiple gadgets.

    Args:
        request: The incoming HTTP request.
        ids: Comma-separated list of gadget IDs to edit.
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
            "resource_config": GADGET_RESOURCE_CONFIG,
            "form_action": "/ui/v1/gadgets/actions/bulk/update",
            "form_title": f"Edit {len(id_list)} Gadgets",
            "bulk_edit": True,
            "bulk_ids": id_list,
            "bulk_count": len(id_list),
        },
    )


@webui_gadgets_router.post(
    path="/actions/bulk/update",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def gadget_bulk_update(
    request: Request,
    service: WebUIGadgetService = Depends(get_gadget_service),
    session: Optional[SessionData] = Depends(get_current_session),
    settings: AppSettings = Depends(get_settings),
) -> HTMLResponse | RedirectResponse:
    """
    Handle bulk gadget update form submission.

    Parses the form data to determine which fields were submitted (enabled
    via the Apply checkbox) and applies those updates to all selected gadgets.

    Args:
        request: The incoming HTTP request.
        service: The gadget service.
        session: The current user session, if any.
        settings: The application settings.

    Returns:
        HTMLResponse | RedirectResponse: Updated gadget list or a redirect.
    """
    if session is None:
        return login_redirect(request)

    form_data = await request.form()
    ids: list[str] = [str(i) for i in form_data.getlist("ids")]

    update_fields = parse_resource_form_fields(form_data, GADGET_RESOURCE_CONFIG)

    if update_fields:
        payload = GadgetUpdate(**update_fields)  # type: ignore[arg-type]
        try:
            await service.bulk_update_gadgets(ids, payload)
        except GadgetApiException as exc:
            logger.warning(f"Failed to bulk update gadgets: {exc}")

    response = HTMLResponse(content="")
    response.headers["HX-Trigger"] = json.dumps(
        {"closeDetailPanel": None, "refreshList": None}
    )
    response.headers["HX-Reswap"] = "none"
    return response


@webui_gadgets_router.post(
    path="/{gadget_id}/zap",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def gadget_zap(
    request: Request,
    gadget_id: str,
    duration: int = Form(10),
    service: WebUIGadgetService = Depends(get_gadget_service),
    session: Optional[SessionData] = Depends(get_current_session),
) -> HTMLResponse | RedirectResponse:
    """
    Initiate a zap operation on a gadget.

    Args:
        request: The incoming HTTP request.
        gadget_id: The ID of the gadget to zap.
        duration: The zap duration in seconds.
        service: The gadget service.
        session: The current user session, if any.

    Returns:
        HTMLResponse | RedirectResponse: The zap status or a redirect.
    """
    if session is None:
        return login_redirect(request)

    try:
        task = await service.zap_gadget(gadget_id, GadgetZap(duration=duration))
        return templates.TemplateResponse(
            request,
            "v1/partials/crud/zap_status.html",
            context={
                "request": request,
                "item_id": gadget_id,
                "task": task,
                "resource_config": GADGET_RESOURCE_CONFIG,
            },
        )
    except GadgetApiException as exc:
        logger.warning(f"Failed to zap gadget {gadget_id}: {exc}")
        return HTMLResponse(
            content="<p class='p-4 text-rose-600'>Failed to start zap.</p>",
            status_code=500,
        )


@webui_gadgets_router.get(
    path="/{gadget_id}/zap/{task_uuid}/status",
    response_class=HTMLResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def gadget_zap_status(
    request: Request,
    gadget_id: str,
    task_uuid: str,
    service: WebUIGadgetService = Depends(get_gadget_service),
    session: Optional[SessionData] = Depends(get_current_session),
) -> HTMLResponse | RedirectResponse:
    """
    Poll for zap task status.

    Args:
        request: The incoming HTTP request.
        gadget_id: The ID of the gadget being zapped.
        task_uuid: The UUID of the zap task.
        service: The gadget service.
        session: The current user session, if any.

    Returns:
        HTMLResponse | RedirectResponse: Updated task status or a redirect.
    """
    if session is None:
        return login_redirect(request)

    try:
        task = await service.get_zap_status(gadget_id, task_uuid)
    except GadgetApiException:
        return HTMLResponse(
            content="<p class='p-4 text-rose-600'>Failed to get status.</p>",
            status_code=500,
        )

    return templates.TemplateResponse(
        request,
        "v1/partials/crud/zap_status.html",
        context={
            "request": request,
            "item_id": gadget_id,
            "task": task,
            "resource_config": GADGET_RESOURCE_CONFIG,
        },
    )
