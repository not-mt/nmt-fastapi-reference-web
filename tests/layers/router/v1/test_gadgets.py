# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for gadget web UI router."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient
from nmtfast.auth.v1.sessions import SessionData
from nmtfast.htmx.v1.schemas import PaginationMeta
from nmtfast.repositories.gadgets.v1.exceptions import GadgetApiException
from nmtfast.repositories.gadgets.v1.schemas import GadgetRead, GadgetZapTask

from app.dependencies.v1.preferences import get_user_page_size
from app.dependencies.v1.session import get_current_session
from app.dependencies.v1.settings import get_settings
from app.layers.router.v1.gadgets import get_gadget_service
from app.layers.service.v1.gadgets import WebUIGadgetService
from app.main import app

client = TestClient(app, follow_redirects=False)

MOCK_GADGET = GadgetRead(id="g1", name="Test", height="10", mass="5", force=20)
MOCK_PAGINATION = PaginationMeta(total=1, page=1, page_size=10)
MOCK_ZAP_TASK = GadgetZapTask(
    uuid="abc", state="RUNNING", id="g1", duration=10, runtime=0
)


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
    Fixture providing a mock WebUIGadgetService.
    """
    svc = MagicMock()
    svc.list_gadgets = AsyncMock(return_value=([MOCK_GADGET], MOCK_PAGINATION))
    svc.get_gadget = AsyncMock(return_value=MOCK_GADGET)
    svc.create_gadget = AsyncMock(return_value=MOCK_GADGET)
    svc.update_gadget = AsyncMock(return_value=MOCK_GADGET)
    svc.delete_gadget = AsyncMock(return_value=None)
    svc.bulk_delete_gadgets = AsyncMock(return_value=2)
    svc.bulk_update_gadgets = AsyncMock(return_value=2)
    svc.zap_gadget = AsyncMock(return_value=MOCK_ZAP_TASK)
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
    app.dependency_overrides[get_gadget_service] = lambda: mock_service
    app.dependency_overrides[get_current_session] = lambda: session


def _cleanup():
    """
    Remove dependency overrides.
    """
    app.dependency_overrides.pop(get_gadget_service, None)
    app.dependency_overrides.pop(get_current_session, None)


# ── gadget_list ──


def test_gadget_list_no_session(mock_service):
    """
    Test GET /ui/v1/gadgets redirects when no session.
    """
    _override(mock_service, None)
    try:
        response = client.get("/ui/v1/gadgets")
        assert response.status_code == 302
    finally:
        _cleanup()


def test_gadget_list_success(mock_service, mock_session):
    """
    Test GET /ui/v1/gadgets renders list.
    """
    _override(mock_service, mock_session)
    try:
        response = client.get("/ui/v1/gadgets")
        assert response.status_code == 200
    finally:
        _cleanup()


def test_gadget_list_api_error(mock_service, mock_session):
    """
    Test GET /ui/v1/gadgets handles API errors.
    """
    mock_service.list_gadgets = AsyncMock(
        side_effect=GadgetApiException(httpx.Response(status_code=500, text="err"))
    )
    _override(mock_service, mock_session)
    try:
        response = client.get("/ui/v1/gadgets")
        assert response.status_code == 200
    finally:
        _cleanup()


# ── get_gadget_service dependency ──


def test_get_gadget_service_dependency():
    """
    Test that get_gadget_service returns a WebUIGadgetService instance.
    """
    svc = get_gadget_service(api_client=MagicMock())
    assert isinstance(svc, WebUIGadgetService)


# ── gadget_create_form ──


def test_gadget_create_form(mock_service, mock_session):
    """
    Test GET /ui/v1/gadgets/create renders form.
    """
    _override(mock_service, mock_session)
    try:
        response = client.get("/ui/v1/gadgets/create")
        assert response.status_code == 200
    finally:
        _cleanup()


def test_gadget_create_form_no_session(mock_service):
    """
    Test GET /ui/v1/gadgets/create redirects when no session.
    """
    _override(mock_service, None)
    try:
        response = client.get("/ui/v1/gadgets/create")
        assert response.status_code == 302
    finally:
        _cleanup()


# ── gadget_create ──


def test_gadget_create_submit(mock_service, mock_session):
    """
    Test POST /ui/v1/gadgets creates a gadget.
    """
    _override(mock_service, mock_session)
    try:
        response = client.post(
            "/ui/v1/gadgets",
            data={"name": "New Gadget"},
        )
        assert response.status_code == 200
    finally:
        _cleanup()


def test_gadget_create_no_session(mock_service):
    """
    Test POST /ui/v1/gadgets redirects when no session.
    """
    _override(mock_service, None)
    try:
        response = client.post("/ui/v1/gadgets", data={"name": "X"})
        assert response.status_code == 302
    finally:
        _cleanup()


def test_gadget_create_api_error(mock_service, mock_session):
    """
    Test POST /ui/v1/gadgets handles create and list API errors.
    """
    mock_service.create_gadget = AsyncMock(
        side_effect=GadgetApiException(httpx.Response(status_code=500, text="err"))
    )
    mock_service.list_gadgets = AsyncMock(
        side_effect=GadgetApiException(httpx.Response(status_code=500, text="err"))
    )
    _override(mock_service, mock_session)
    try:
        response = client.post("/ui/v1/gadgets", data={"name": "X"})
        assert response.status_code == 200
    finally:
        _cleanup()


# ── gadget_detail ──


def test_gadget_detail_htmx(mock_service, mock_session):
    """
    Test GET /ui/v1/gadgets/{id} returns partial for HTMX.
    """
    _override(mock_service, mock_session)
    try:
        response = client.get("/ui/v1/gadgets/g1", headers={"HX-Request": "true"})
        assert response.status_code == 200
    finally:
        _cleanup()


def test_gadget_detail_full_page(mock_service, mock_session):
    """
    Test GET /ui/v1/gadgets/{id} returns full page for deep link.
    """
    _override(mock_service, mock_session)
    try:
        response = client.get("/ui/v1/gadgets/g1")
        assert response.status_code == 200
    finally:
        _cleanup()


def test_gadget_detail_full_page_list_error(mock_service, mock_session):
    """
    Test GET /ui/v1/gadgets/{id} full page handles list API error.
    """
    mock_service.list_gadgets = AsyncMock(
        side_effect=GadgetApiException(httpx.Response(status_code=500, text="err"))
    )
    _override(mock_service, mock_session)
    try:
        response = client.get("/ui/v1/gadgets/g1")
        assert response.status_code == 200
    finally:
        _cleanup()


def test_gadget_detail_not_found(mock_service, mock_session):
    """
    Test GET /ui/v1/gadgets/{id} returns 404 on API error.
    """
    mock_service.get_gadget = AsyncMock(
        side_effect=GadgetApiException(
            httpx.Response(status_code=404, text="not found")
        )
    )
    _override(mock_service, mock_session)
    try:
        response = client.get("/ui/v1/gadgets/g1")
        assert response.status_code == 404
    finally:
        _cleanup()


def test_gadget_detail_no_session(mock_service):
    """
    Test GET /ui/v1/gadgets/{id} redirects when no session.
    """
    _override(mock_service, None)
    try:
        response = client.get("/ui/v1/gadgets/g1")
        assert response.status_code == 302
    finally:
        _cleanup()


# ── gadget_edit_form ──


def test_gadget_edit_form(mock_service, mock_session):
    """
    Test GET /ui/v1/gadgets/{id}/edit renders edit form.
    """
    _override(mock_service, mock_session)
    try:
        response = client.get("/ui/v1/gadgets/g1/edit")
        assert response.status_code == 200
    finally:
        _cleanup()


def test_gadget_edit_form_not_found(mock_service, mock_session):
    """
    Test GET /ui/v1/gadgets/{id}/edit returns 404 on API error.
    """
    mock_service.get_gadget = AsyncMock(
        side_effect=GadgetApiException(
            httpx.Response(status_code=404, text="not found")
        )
    )
    _override(mock_service, mock_session)
    try:
        response = client.get("/ui/v1/gadgets/g1/edit")
        assert response.status_code == 404
    finally:
        _cleanup()


def test_gadget_edit_form_no_session(mock_service):
    """
    Test GET /ui/v1/gadgets/{id}/edit redirects when no session.
    """
    _override(mock_service, None)
    try:
        response = client.get("/ui/v1/gadgets/g1/edit")
        assert response.status_code == 302
    finally:
        _cleanup()


# ── gadget_update ──


def test_gadget_update(mock_service, mock_session):
    """
    Test PATCH /ui/v1/gadgets/{id} updates a gadget.
    """
    _override(mock_service, mock_session)
    try:
        response = client.patch(
            "/ui/v1/gadgets/g1",
            data={"name": "Updated"},
        )
        assert response.status_code == 200
        assert response.headers.get("hx-trigger") == "refreshList"
    finally:
        _cleanup()


def test_gadget_update_no_session(mock_service):
    """
    Test PATCH /ui/v1/gadgets/{id} redirects when no session.
    """
    _override(mock_service, None)
    try:
        response = client.patch("/ui/v1/gadgets/g1", data={"name": "X"})
        assert response.status_code == 302
    finally:
        _cleanup()


def test_gadget_update_api_error(mock_service, mock_session):
    """
    Test PATCH /ui/v1/gadgets/{id} handles update and get errors.
    """
    mock_service.update_gadget = AsyncMock(
        side_effect=GadgetApiException(httpx.Response(status_code=500, text="err"))
    )
    mock_service.get_gadget = AsyncMock(
        side_effect=GadgetApiException(
            httpx.Response(status_code=404, text="not found")
        )
    )
    _override(mock_service, mock_session)
    try:
        response = client.patch("/ui/v1/gadgets/g1", data={"name": "X"})
        assert response.status_code == 404
    finally:
        _cleanup()


# ── gadget_delete ──


def test_gadget_delete_success(mock_service, mock_session):
    """
    Test DELETE /ui/v1/gadgets/{id} deletes a gadget.
    """
    _override(mock_service, mock_session)
    try:
        response = client.delete("/ui/v1/gadgets/g1")
        assert response.status_code == 200
        assert "deleteSuccess" in response.headers.get("hx-trigger", "")
    finally:
        _cleanup()


def test_gadget_delete_no_session(mock_service):
    """
    Test DELETE /ui/v1/gadgets/{id} redirects when no session.
    """
    _override(mock_service, None)
    try:
        response = client.delete("/ui/v1/gadgets/g1")
        assert response.status_code == 302
    finally:
        _cleanup()


def test_gadget_delete_api_error(mock_service, mock_session):
    """
    Test DELETE /ui/v1/gadgets/{id} renders error on API failure.
    """
    mock_service.delete_gadget = AsyncMock(
        side_effect=GadgetApiException(httpx.Response(status_code=409, text="conflict"))
    )
    _override(mock_service, mock_session)
    try:
        response = client.delete("/ui/v1/gadgets/g1")
        assert response.status_code == 200
    finally:
        _cleanup()


def test_gadget_delete_list_error(mock_service, mock_session):
    """
    Test DELETE /ui/v1/gadgets/{id} handles list API error after delete.
    """
    mock_service.list_gadgets = AsyncMock(
        side_effect=GadgetApiException(httpx.Response(status_code=500, text="err"))
    )
    _override(mock_service, mock_session)
    try:
        response = client.delete("/ui/v1/gadgets/g1")
        assert response.status_code == 200
    finally:
        _cleanup()


# ── gadget_bulk_delete ──


def test_gadget_bulk_delete(mock_service, mock_session):
    """
    Test POST /ui/v1/gadgets/actions/bulk/delete.
    """
    _override(mock_service, mock_session)
    try:
        response = client.post(
            "/ui/v1/gadgets/actions/bulk/delete",
            json={"ids": ["g1", "g2"]},
        )
        assert response.status_code == 200
    finally:
        _cleanup()


def test_gadget_bulk_delete_no_session(mock_service):
    """
    Test POST /ui/v1/gadgets/actions/bulk/delete redirects when no session.
    """
    _override(mock_service, None)
    try:
        response = client.post(
            "/ui/v1/gadgets/actions/bulk/delete",
            json={"ids": ["g1"]},
        )
        assert response.status_code == 302
    finally:
        _cleanup()


def test_gadget_bulk_delete_api_error(mock_service, mock_session):
    """
    Test bulk delete handles both delete and list API errors.
    """
    mock_service.bulk_delete_gadgets = AsyncMock(
        side_effect=GadgetApiException(httpx.Response(status_code=500, text="err"))
    )
    mock_service.list_gadgets = AsyncMock(
        side_effect=GadgetApiException(httpx.Response(status_code=500, text="err"))
    )
    _override(mock_service, mock_session)
    try:
        response = client.post(
            "/ui/v1/gadgets/actions/bulk/delete",
            json={"ids": ["g1"]},
        )
        assert response.status_code == 200
    finally:
        _cleanup()


# ── gadget_bulk_edit_form ──


def test_gadget_bulk_edit_form(mock_service, mock_session):
    """
    Test GET /ui/v1/gadgets/actions/bulk/edit renders form.
    """
    _override(mock_service, mock_session)
    try:
        response = client.get(
            "/ui/v1/gadgets/actions/bulk/edit", params={"ids": "g1,g2"}
        )
        assert response.status_code == 200
    finally:
        _cleanup()


def test_gadget_bulk_edit_form_no_session(mock_service):
    """
    Test GET /ui/v1/gadgets/actions/bulk/edit redirects when no session.
    """
    _override(mock_service, None)
    try:
        response = client.get("/ui/v1/gadgets/actions/bulk/edit", params={"ids": "g1"})
        assert response.status_code == 302
    finally:
        _cleanup()


# ── gadget_bulk_update ──


def test_gadget_bulk_update(mock_service, mock_session):
    """
    Test POST /ui/v1/gadgets/actions/bulk/update.
    """
    _override(mock_service, mock_session)
    try:
        response = client.post(
            "/ui/v1/gadgets/actions/bulk/update",
            data={"ids": ["g1", "g2"], "name": "Bulk"},
        )
        assert response.status_code == 200
    finally:
        _cleanup()


def test_gadget_bulk_update_no_session(mock_service):
    """
    Test POST /ui/v1/gadgets/actions/bulk/update redirects when no session.
    """
    _override(mock_service, None)
    try:
        response = client.post(
            "/ui/v1/gadgets/actions/bulk/update",
            data={"ids": ["g1"], "name": "X"},
        )
        assert response.status_code == 302
    finally:
        _cleanup()


def test_gadget_bulk_update_with_number_field(mock_service, mock_session):
    """
    Test POST /ui/v1/gadgets/actions/bulk/update with a number field.
    """
    _override(mock_service, mock_session)
    try:
        response = client.post(
            "/ui/v1/gadgets/actions/bulk/update",
            data={"ids": ["g1"], "force": "42"},
        )
        assert response.status_code == 200
    finally:
        _cleanup()


def test_gadget_bulk_update_api_error(mock_service, mock_session):
    """
    Test POST /ui/v1/gadgets/actions/bulk/update handles API error.
    """
    mock_service.bulk_update_gadgets = AsyncMock(
        side_effect=GadgetApiException(httpx.Response(status_code=500, text="err"))
    )
    _override(mock_service, mock_session)
    try:
        response = client.post(
            "/ui/v1/gadgets/actions/bulk/update",
            data={"ids": ["g1"], "name": "Bulk"},
        )
        assert response.status_code == 200
    finally:
        _cleanup()


def test_gadget_bulk_update_no_fields(mock_service, mock_session):
    """
    Test POST /ui/v1/gadgets/actions/bulk/update with no matching fields.
    """
    _override(mock_service, mock_session)
    try:
        response = client.post(
            "/ui/v1/gadgets/actions/bulk/update",
            data={"ids": ["g1"]},
        )
        assert response.status_code == 200
    finally:
        _cleanup()


# ── gadget_zap ──


def test_gadget_zap_success(mock_service, mock_session):
    """
    Test POST /ui/v1/gadgets/{id}/zap initiates zap.
    """
    _override(mock_service, mock_session)
    try:
        response = client.post(
            "/ui/v1/gadgets/g1/zap",
            data={"duration": "10"},
        )
        assert response.status_code == 200
    finally:
        _cleanup()


def test_gadget_zap_no_session(mock_service):
    """
    Test POST /ui/v1/gadgets/{id}/zap redirects when no session.
    """
    _override(mock_service, None)
    try:
        response = client.post("/ui/v1/gadgets/g1/zap", data={"duration": "10"})
        assert response.status_code == 302
    finally:
        _cleanup()


def test_gadget_zap_api_error(mock_service, mock_session):
    """
    Test POST /ui/v1/gadgets/{id}/zap returns 500 on API error.
    """
    mock_service.zap_gadget = AsyncMock(
        side_effect=GadgetApiException(httpx.Response(status_code=500, text="err"))
    )
    _override(mock_service, mock_session)
    try:
        response = client.post(
            "/ui/v1/gadgets/g1/zap",
            data={"duration": "10"},
        )
        assert response.status_code == 500
    finally:
        _cleanup()


# ── gadget_zap_status ──


def test_gadget_zap_status_success(mock_service, mock_session):
    """
    Test GET /ui/v1/gadgets/{id}/zap/{uuid}/status.
    """
    _override(mock_service, mock_session)
    try:
        response = client.get("/ui/v1/gadgets/g1/zap/abc/status")
        assert response.status_code == 200
    finally:
        _cleanup()


def test_gadget_zap_status_no_session(mock_service):
    """
    Test GET /ui/v1/gadgets/{id}/zap/{uuid}/status redirects.
    """
    _override(mock_service, None)
    try:
        response = client.get("/ui/v1/gadgets/g1/zap/abc/status")
        assert response.status_code == 302
    finally:
        _cleanup()


def test_gadget_zap_status_api_error(mock_service, mock_session):
    """
    Test GET /ui/v1/gadgets/{id}/zap/{uuid}/status returns 500 on error.
    """
    mock_service.get_zap_status = AsyncMock(
        side_effect=GadgetApiException(httpx.Response(status_code=500, text="err"))
    )
    _override(mock_service, mock_session)
    try:
        response = client.get("/ui/v1/gadgets/g1/zap/abc/status")
        assert response.status_code == 500
    finally:
        _cleanup()
