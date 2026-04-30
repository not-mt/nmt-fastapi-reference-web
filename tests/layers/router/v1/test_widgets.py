# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for widget web UI router."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient
from nmtfast.auth.v1.sessions import SessionData
from nmtfast.htmx.v1.schemas import PaginationMeta
from nmtfast.repositories.widgets.v1.exceptions import WidgetApiException
from nmtfast.repositories.widgets.v1.schemas import WidgetRead, WidgetZapTask

from app.dependencies.v1.preferences import get_user_page_size
from app.dependencies.v1.session import get_current_session
from app.dependencies.v1.settings import get_settings
from app.layers.router.v1.widgets import get_widget_service
from app.layers.service.v1.widgets import WebUIWidgetService
from app.main import app

client = TestClient(app, follow_redirects=False)

MOCK_WIDGET = WidgetRead(id=1, name="Test", height="10", mass="5", force=20)
MOCK_PAGINATION = PaginationMeta(total=1, page=1, page_size=10)
MOCK_ZAP_TASK = WidgetZapTask(uuid="abc", state="RUNNING", id=1, duration=10, runtime=0)


@pytest.fixture
def mock_session():
    """
    Fixture providing a mock SessionData.
    """
    session = MagicMock(spec=SessionData)
    session.user_name = "Test User"
    session.user_id = "user-123"
    session.user_claims = {"sub": "user-123"}
    session.acls = []
    session.access_token = "fake"
    return session


@pytest.fixture
def mock_service():
    """
    Fixture providing a mock WebUIWidgetService.
    """
    svc = MagicMock()
    svc.list_widgets = AsyncMock(return_value=([MOCK_WIDGET], MOCK_PAGINATION))
    svc.get_widget = AsyncMock(return_value=MOCK_WIDGET)
    svc.create_widget = AsyncMock(return_value=MOCK_WIDGET)
    svc.update_widget = AsyncMock(return_value=MOCK_WIDGET)
    svc.delete_widget = AsyncMock(return_value=None)
    svc.bulk_delete_widgets = AsyncMock(return_value=2)
    svc.bulk_update_widgets = AsyncMock(return_value=2)
    svc.zap_widget = AsyncMock(return_value=MOCK_ZAP_TASK)
    svc.get_zap_status = AsyncMock(return_value=MOCK_ZAP_TASK)
    return svc


@pytest.fixture
def mock_settings():
    """
    Fixture providing mock AppSettings.
    """
    settings = MagicMock()
    settings.app_name = "Test App"
    return settings


@pytest.fixture(autouse=True)
def _override_settings(mock_settings):
    """
    Auto-override settings dependency for all tests.
    """
    app.dependency_overrides[get_settings] = lambda: mock_settings
    app.dependency_overrides[get_user_page_size] = lambda: 10
    yield
    app.dependency_overrides.pop(get_settings, None)
    app.dependency_overrides.pop(get_user_page_size, None)


def _override(mock_service, session):
    """
    Set dependency overrides for service and session.
    """
    app.dependency_overrides[get_widget_service] = lambda: mock_service
    app.dependency_overrides[get_current_session] = lambda: session


def _cleanup():
    """
    Remove dependency overrides.
    """
    app.dependency_overrides.pop(get_widget_service, None)
    app.dependency_overrides.pop(get_current_session, None)


# ── widget_list ──


def test_widget_list_no_session(mock_service):
    """
    Test GET /ui/v1/widgets redirects when no session.
    """
    _override(mock_service, None)
    try:
        response = client.get("/ui/v1/widgets")
        assert response.status_code == 302
    finally:
        _cleanup()


def test_widget_list_success(mock_service, mock_session):
    """
    Test GET /ui/v1/widgets renders list.
    """
    _override(mock_service, mock_session)
    try:
        response = client.get("/ui/v1/widgets")
        assert response.status_code == 200
    finally:
        _cleanup()


def test_widget_list_api_error(mock_service, mock_session):
    """
    Test GET /ui/v1/widgets handles API errors.
    """
    mock_service.list_widgets = AsyncMock(
        side_effect=WidgetApiException(httpx.Response(status_code=500, text="err"))
    )
    _override(mock_service, mock_session)
    try:
        response = client.get("/ui/v1/widgets")
        assert response.status_code == 200
    finally:
        _cleanup()


# ── get_widget_service dependency ──


def test_get_widget_service_dependency():
    """
    Test that get_widget_service returns a WebUIWidgetService instance.
    """
    svc = get_widget_service(api_client=MagicMock())
    assert isinstance(svc, WebUIWidgetService)


# ── widget_create_form ──


def test_widget_create_form(mock_service, mock_session):
    """
    Test GET /ui/v1/widgets/create renders form.
    """
    _override(mock_service, mock_session)
    try:
        response = client.get("/ui/v1/widgets/create")
        assert response.status_code == 200
    finally:
        _cleanup()


def test_widget_create_form_no_session(mock_service):
    """
    Test GET /ui/v1/widgets/create redirects when no session.
    """
    _override(mock_service, None)
    try:
        response = client.get("/ui/v1/widgets/create")
        assert response.status_code == 302
    finally:
        _cleanup()


# ── widget_create ──


def test_widget_create_submit(mock_service, mock_session):
    """
    Test POST /ui/v1/widgets creates a widget.
    """
    _override(mock_service, mock_session)
    try:
        response = client.post(
            "/ui/v1/widgets",
            data={"name": "New Widget"},
        )
        assert response.status_code == 200
    finally:
        _cleanup()


def test_widget_create_no_session(mock_service):
    """
    Test POST /ui/v1/widgets redirects when no session.
    """
    _override(mock_service, None)
    try:
        response = client.post("/ui/v1/widgets", data={"name": "X"})
        assert response.status_code == 302
    finally:
        _cleanup()


def test_widget_create_api_error(mock_service, mock_session):
    """
    Test POST /ui/v1/widgets handles create and list API errors.
    """
    mock_service.create_widget = AsyncMock(
        side_effect=WidgetApiException(httpx.Response(status_code=500, text="err"))
    )
    mock_service.list_widgets = AsyncMock(
        side_effect=WidgetApiException(httpx.Response(status_code=500, text="err"))
    )
    _override(mock_service, mock_session)
    try:
        response = client.post("/ui/v1/widgets", data={"name": "X"})
        assert response.status_code == 200
    finally:
        _cleanup()


# ── widget_detail ──


def test_widget_detail_htmx(mock_service, mock_session):
    """
    Test GET /ui/v1/widgets/{id} returns partial for HTMX.
    """
    _override(mock_service, mock_session)
    try:
        response = client.get("/ui/v1/widgets/1", headers={"HX-Request": "true"})
        assert response.status_code == 200
    finally:
        _cleanup()


def test_widget_detail_full_page(mock_service, mock_session):
    """
    Test GET /ui/v1/widgets/{id} returns full page for deep link.
    """
    _override(mock_service, mock_session)
    try:
        response = client.get("/ui/v1/widgets/1")
        assert response.status_code == 200
    finally:
        _cleanup()


def test_widget_detail_full_page_list_error(mock_service, mock_session):
    """
    Test GET /ui/v1/widgets/{id} full page handles list API error.
    """
    mock_service.list_widgets = AsyncMock(
        side_effect=WidgetApiException(httpx.Response(status_code=500, text="err"))
    )
    _override(mock_service, mock_session)
    try:
        response = client.get("/ui/v1/widgets/1")
        assert response.status_code == 200
    finally:
        _cleanup()


def test_widget_detail_not_found(mock_service, mock_session):
    """
    Test GET /ui/v1/widgets/{id} returns 404 on API error.
    """
    mock_service.get_widget = AsyncMock(
        side_effect=WidgetApiException(
            httpx.Response(status_code=404, text="not found")
        )
    )
    _override(mock_service, mock_session)
    try:
        response = client.get("/ui/v1/widgets/1")
        assert response.status_code == 404
    finally:
        _cleanup()


def test_widget_detail_no_session(mock_service):
    """
    Test GET /ui/v1/widgets/{id} redirects when no session.
    """
    _override(mock_service, None)
    try:
        response = client.get("/ui/v1/widgets/1")
        assert response.status_code == 302
    finally:
        _cleanup()


# ── widget_edit_form ──


def test_widget_edit_form(mock_service, mock_session):
    """
    Test GET /ui/v1/widgets/{id}/edit renders edit form.
    """
    _override(mock_service, mock_session)
    try:
        response = client.get("/ui/v1/widgets/1/edit")
        assert response.status_code == 200
    finally:
        _cleanup()


def test_widget_edit_form_not_found(mock_service, mock_session):
    """
    Test GET /ui/v1/widgets/{id}/edit returns 404 on API error.
    """
    mock_service.get_widget = AsyncMock(
        side_effect=WidgetApiException(
            httpx.Response(status_code=404, text="not found")
        )
    )
    _override(mock_service, mock_session)
    try:
        response = client.get("/ui/v1/widgets/1/edit")
        assert response.status_code == 404
    finally:
        _cleanup()


def test_widget_edit_form_no_session(mock_service):
    """
    Test GET /ui/v1/widgets/{id}/edit redirects when no session.
    """
    _override(mock_service, None)
    try:
        response = client.get("/ui/v1/widgets/1/edit")
        assert response.status_code == 302
    finally:
        _cleanup()


# ── widget_update ──


def test_widget_update(mock_service, mock_session):
    """
    Test PATCH /ui/v1/widgets/{id} updates a widget.
    """
    _override(mock_service, mock_session)
    try:
        response = client.patch(
            "/ui/v1/widgets/1",
            data={"name": "Updated"},
        )
        assert response.status_code == 200
        assert response.headers.get("hx-trigger") == "refreshList"
    finally:
        _cleanup()


def test_widget_update_no_session(mock_service):
    """
    Test PATCH /ui/v1/widgets/{id} redirects when no session.
    """
    _override(mock_service, None)
    try:
        response = client.patch("/ui/v1/widgets/1", data={"name": "X"})
        assert response.status_code == 302
    finally:
        _cleanup()


def test_widget_update_api_error(mock_service, mock_session):
    """
    Test PATCH /ui/v1/widgets/{id} handles update and get errors.
    """
    mock_service.update_widget = AsyncMock(
        side_effect=WidgetApiException(httpx.Response(status_code=500, text="err"))
    )
    mock_service.get_widget = AsyncMock(
        side_effect=WidgetApiException(
            httpx.Response(status_code=404, text="not found")
        )
    )
    _override(mock_service, mock_session)
    try:
        response = client.patch("/ui/v1/widgets/1", data={"name": "X"})
        assert response.status_code == 404
    finally:
        _cleanup()


# ── widget_delete ──


def test_widget_delete_success(mock_service, mock_session):
    """
    Test DELETE /ui/v1/widgets/{id} deletes a widget.
    """
    _override(mock_service, mock_session)
    try:
        response = client.delete("/ui/v1/widgets/1")
        assert response.status_code == 200
        assert "deleteSuccess" in response.headers.get("hx-trigger", "")
    finally:
        _cleanup()


def test_widget_delete_no_session(mock_service):
    """
    Test DELETE /ui/v1/widgets/{id} redirects when no session.
    """
    _override(mock_service, None)
    try:
        response = client.delete("/ui/v1/widgets/1")
        assert response.status_code == 302
    finally:
        _cleanup()


def test_widget_delete_api_error(mock_service, mock_session):
    """
    Test DELETE /ui/v1/widgets/{id} renders error on API failure.
    """
    mock_service.delete_widget = AsyncMock(
        side_effect=WidgetApiException(httpx.Response(status_code=409, text="conflict"))
    )
    _override(mock_service, mock_session)
    try:
        response = client.delete("/ui/v1/widgets/1")
        assert response.status_code == 200
    finally:
        _cleanup()


def test_widget_delete_list_error(mock_service, mock_session):
    """
    Test DELETE /ui/v1/widgets/{id} handles list API error after delete.
    """
    mock_service.list_widgets = AsyncMock(
        side_effect=WidgetApiException(httpx.Response(status_code=500, text="err"))
    )
    _override(mock_service, mock_session)
    try:
        response = client.delete("/ui/v1/widgets/1")
        assert response.status_code == 200
    finally:
        _cleanup()


# ── widget_bulk_delete ──


def test_widget_bulk_delete(mock_service, mock_session):
    """
    Test POST /ui/v1/widgets/actions/bulk/delete.
    """
    _override(mock_service, mock_session)
    try:
        response = client.post(
            "/ui/v1/widgets/actions/bulk/delete",
            json={"ids": [1, 2]},
        )
        assert response.status_code == 200
    finally:
        _cleanup()


def test_widget_bulk_delete_no_session(mock_service):
    """
    Test POST /ui/v1/widgets/actions/bulk/delete redirects when no session.
    """
    _override(mock_service, None)
    try:
        response = client.post(
            "/ui/v1/widgets/actions/bulk/delete",
            json={"ids": [1]},
        )
        assert response.status_code == 302
    finally:
        _cleanup()


def test_widget_bulk_delete_api_error(mock_service, mock_session):
    """
    Test bulk delete handles both delete and list API errors.
    """
    mock_service.bulk_delete_widgets = AsyncMock(
        side_effect=WidgetApiException(httpx.Response(status_code=500, text="err"))
    )
    mock_service.list_widgets = AsyncMock(
        side_effect=WidgetApiException(httpx.Response(status_code=500, text="err"))
    )
    _override(mock_service, mock_session)
    try:
        response = client.post(
            "/ui/v1/widgets/actions/bulk/delete",
            json={"ids": [1]},
        )
        assert response.status_code == 200
    finally:
        _cleanup()


# ── widget_bulk_edit_form ──


def test_widget_bulk_edit_form(mock_service, mock_session):
    """
    Test GET /ui/v1/widgets/actions/bulk/edit renders form.
    """
    _override(mock_service, mock_session)
    try:
        response = client.get("/ui/v1/widgets/actions/bulk/edit", params={"ids": "1,2"})
        assert response.status_code == 200
    finally:
        _cleanup()


def test_widget_bulk_edit_form_no_session(mock_service):
    """
    Test GET /ui/v1/widgets/actions/bulk/edit redirects when no session.
    """
    _override(mock_service, None)
    try:
        response = client.get("/ui/v1/widgets/actions/bulk/edit", params={"ids": "1"})
        assert response.status_code == 302
    finally:
        _cleanup()


# ── widget_bulk_update ──


def test_widget_bulk_update(mock_service, mock_session):
    """
    Test POST /ui/v1/widgets/actions/bulk/update.
    """
    _override(mock_service, mock_session)
    try:
        response = client.post(
            "/ui/v1/widgets/actions/bulk/update",
            data={"ids": ["1", "2"], "name": "Bulk"},
        )
        assert response.status_code == 200
    finally:
        _cleanup()


def test_widget_bulk_update_no_session(mock_service):
    """
    Test POST /ui/v1/widgets/actions/bulk/update redirects when no session.
    """
    _override(mock_service, None)
    try:
        response = client.post(
            "/ui/v1/widgets/actions/bulk/update",
            data={"ids": ["1"], "name": "X"},
        )
        assert response.status_code == 302
    finally:
        _cleanup()


def test_widget_bulk_update_with_number_field(mock_service, mock_session):
    """
    Test POST /ui/v1/widgets/actions/bulk/update with a number field.
    """
    _override(mock_service, mock_session)
    try:
        response = client.post(
            "/ui/v1/widgets/actions/bulk/update",
            data={"ids": ["1"], "force": "42"},
        )
        assert response.status_code == 200
    finally:
        _cleanup()


def test_widget_bulk_update_api_error(mock_service, mock_session):
    """
    Test POST /ui/v1/widgets/actions/bulk/update handles API error.
    """
    mock_service.bulk_update_widgets = AsyncMock(
        side_effect=WidgetApiException(httpx.Response(status_code=500, text="err"))
    )
    _override(mock_service, mock_session)
    try:
        response = client.post(
            "/ui/v1/widgets/actions/bulk/update",
            data={"ids": ["1"], "name": "Bulk"},
        )
        assert response.status_code == 200
    finally:
        _cleanup()


def test_widget_bulk_update_no_fields(mock_service, mock_session):
    """
    Test POST /ui/v1/widgets/actions/bulk/update with no matching fields.
    """
    _override(mock_service, mock_session)
    try:
        response = client.post(
            "/ui/v1/widgets/actions/bulk/update",
            data={"ids": ["1"]},
        )
        assert response.status_code == 200
    finally:
        _cleanup()


# ── widget_zap ──


def test_widget_zap_success(mock_service, mock_session):
    """
    Test POST /ui/v1/widgets/{id}/zap initiates zap.
    """
    _override(mock_service, mock_session)
    try:
        response = client.post(
            "/ui/v1/widgets/1/zap",
            data={"duration": "10"},
        )
        assert response.status_code == 200
    finally:
        _cleanup()


def test_widget_zap_no_session(mock_service):
    """
    Test POST /ui/v1/widgets/{id}/zap redirects when no session.
    """
    _override(mock_service, None)
    try:
        response = client.post("/ui/v1/widgets/1/zap", data={"duration": "10"})
        assert response.status_code == 302
    finally:
        _cleanup()


def test_widget_zap_api_error(mock_service, mock_session):
    """
    Test POST /ui/v1/widgets/{id}/zap returns 500 on API error.
    """
    mock_service.zap_widget = AsyncMock(
        side_effect=WidgetApiException(httpx.Response(status_code=500, text="err"))
    )
    _override(mock_service, mock_session)
    try:
        response = client.post(
            "/ui/v1/widgets/1/zap",
            data={"duration": "10"},
        )
        assert response.status_code == 500
    finally:
        _cleanup()


# ── widget_zap_status ──


def test_widget_zap_status_success(mock_service, mock_session):
    """
    Test GET /ui/v1/widgets/{id}/zap/{uuid}/status.
    """
    _override(mock_service, mock_session)
    try:
        response = client.get("/ui/v1/widgets/1/zap/abc/status")
        assert response.status_code == 200
    finally:
        _cleanup()


def test_widget_zap_status_no_session(mock_service):
    """
    Test GET /ui/v1/widgets/{id}/zap/{uuid}/status redirects.
    """
    _override(mock_service, None)
    try:
        response = client.get("/ui/v1/widgets/1/zap/abc/status")
        assert response.status_code == 302
    finally:
        _cleanup()


def test_widget_zap_status_api_error(mock_service, mock_session):
    """
    Test GET /ui/v1/widgets/{id}/zap/{uuid}/status returns 500 on error.
    """
    mock_service.get_zap_status = AsyncMock(
        side_effect=WidgetApiException(httpx.Response(status_code=500, text="err"))
    )
    _override(mock_service, mock_session)
    try:
        response = client.get("/ui/v1/widgets/1/zap/abc/status")
        assert response.status_code == 500
    finally:
        _cleanup()
