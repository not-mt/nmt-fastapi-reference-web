# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for webui router layer."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from nmtfast.auth.v1.sessions import SessionData

from app.core.v1.settings import AppSettings
from app.dependencies.v1.api_client import get_api_client
from app.dependencies.v1.mongo import get_mongo_db
from app.dependencies.v1.session import get_current_session
from app.layers.router.v1.main import (
    get_web_user_settings_service,
    get_webui_service,
)
from app.layers.service.v1.main import WebUIService
from app.layers.service.v1.web_user_settings import (
    UserPreferences,
    WebUIUserSettingsService,
)
from app.main import app

client = TestClient(app, follow_redirects=False)


@pytest.fixture
def mock_webui_service():
    """
    Fixture to provide a mock WebUIService.
    """
    svc = MagicMock()
    svc.dummy_index = AsyncMock(return_value=None)
    return svc


@pytest.fixture
def mock_session_data():
    """
    Fixture providing a mock SessionData.
    """
    session = MagicMock(spec=SessionData)
    session.user_name = "Test User"
    session.user_id = "user-123"
    session.user_claims = {"sub": "user-123", "name": "Test User"}
    session.acls = []
    session.access_token = "fake-access-token"
    session.refresh_token = None
    session.token_expires_at = 9999999999.0
    session.created_at = 1000000000.0
    return session


@pytest.fixture
def mock_api_client():
    """
    Fixture providing a mock httpx.AsyncClient.

    Returns a properly configured mock so that _fetch_dashboard_counts
    succeeds without triggering tenacity retries or unawaited coroutines.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []
    mock_response.headers = {"X-Total-Count": "0"}

    api = MagicMock()
    api.get = AsyncMock(return_value=mock_response)
    return api


@pytest.fixture
def mock_mongo_db():
    """
    Fixture providing a mock MongoDB database.

    Configures the collection so that _fetch_display_name can call
    find_one without creating unawaited coroutines.
    """
    mock_collection = MagicMock()
    mock_collection.find_one = AsyncMock(return_value=None)
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)
    return mock_db


@pytest.fixture
def mock_user_settings_service():
    """
    Fixture providing a mock WebUIUserSettingsService.
    """
    svc = MagicMock()
    svc.get_preferences = AsyncMock(
        return_value=UserPreferences(display_name="Test", timezone="UTC", page_size=10)
    )
    svc.update_preferences = AsyncMock(
        return_value=UserPreferences(
            display_name="Updated", timezone="US/Eastern", page_size=25
        )
    )
    return svc


def test_get_index_redirects_when_no_session(
    mock_webui_service, mock_api_client, mock_mongo_db
):
    """
    Test that GET /ui/v1 redirects to login when no session exists.
    """
    app.dependency_overrides[get_webui_service] = lambda: mock_webui_service
    app.dependency_overrides[get_current_session] = lambda: None
    app.dependency_overrides[get_api_client] = lambda: mock_api_client
    app.dependency_overrides[get_mongo_db] = lambda: mock_mongo_db

    try:
        response = client.get("/ui/v1")
        assert response.status_code == 302
        assert response.headers["location"] == "/ui/v1/login"
    finally:
        app.dependency_overrides.pop(get_webui_service, None)
        app.dependency_overrides.pop(get_current_session, None)
        app.dependency_overrides.pop(get_api_client, None)
        app.dependency_overrides.pop(get_mongo_db, None)


def test_get_index_renders_when_session_exists(
    mock_webui_service, mock_session_data, mock_api_client, mock_mongo_db
):
    """
    Test that GET /ui/v1 renders the index page when a session exists.
    """
    app.dependency_overrides[get_webui_service] = lambda: mock_webui_service
    app.dependency_overrides[get_current_session] = lambda: mock_session_data
    app.dependency_overrides[get_api_client] = lambda: mock_api_client
    app.dependency_overrides[get_mongo_db] = lambda: mock_mongo_db

    try:
        response = client.get("/ui/v1")
        assert response.status_code == 200
        mock_webui_service.dummy_index.assert_awaited_once()
    finally:
        app.dependency_overrides.pop(get_webui_service, None)
        app.dependency_overrides.pop(get_current_session, None)
        app.dependency_overrides.pop(get_api_client, None)
        app.dependency_overrides.pop(get_mongo_db, None)


def test_get_login_page_renders_when_no_session():
    """
    Test that GET /ui/v1/login renders the login page when no session.
    """
    app.dependency_overrides[get_current_session] = lambda: None

    try:
        response = client.get("/ui/v1/login")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_session, None)


def test_get_login_page_redirects_when_session_exists(mock_session_data):
    """
    Test that GET /ui/v1/login redirects to index when session exists.
    """
    app.dependency_overrides[get_current_session] = lambda: mock_session_data

    try:
        response = client.get("/ui/v1/login")
        assert response.status_code == 302
        assert response.headers["location"] == "/ui/v1"
    finally:
        app.dependency_overrides.pop(get_current_session, None)


def test_get_webui_service_dependency():
    """
    Test that get_webui_service returns a WebUIService instance.
    """
    service = get_webui_service(
        db=MagicMock(),
        acls=[],
        settings=MagicMock(spec=AppSettings),
        cache=MagicMock(),
        kafka=None,
    )
    assert isinstance(service, WebUIService)


def test_get_delete_confirm_no_session():
    """
    Test that GET /ui/v1/delete-confirm redirects when no session.
    """
    app.dependency_overrides[get_current_session] = lambda: None

    try:
        response = client.get(
            "/ui/v1/delete-confirm",
            params={
                "delete_url": "/ui/v1/gadgets/1",
                "resource_type": "Gadget",
                "resource_name": "Test",
            },
        )
        assert response.status_code == 302
    finally:
        app.dependency_overrides.pop(get_current_session, None)


def test_get_delete_confirm_with_session(mock_session_data):
    """
    Test that GET /ui/v1/delete-confirm renders when session exists.
    """
    app.dependency_overrides[get_current_session] = lambda: mock_session_data

    try:
        response = client.get(
            "/ui/v1/delete-confirm",
            params={
                "delete_url": "/ui/v1/gadgets/1",
                "resource_type": "Gadget",
                "resource_name": "Test",
            },
        )
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_session, None)


def test_get_delete_confirm_invalid_url(mock_session_data):
    """
    Test that GET /ui/v1/delete-confirm rejects invalid delete URLs.
    """
    app.dependency_overrides[get_current_session] = lambda: mock_session_data

    try:
        response = client.get(
            "/ui/v1/delete-confirm",
            params={
                "delete_url": "https://evil.com/delete",
                "resource_type": "Gadget",
                "resource_name": "Test",
            },
        )
        assert response.status_code == 400
    finally:
        app.dependency_overrides.pop(get_current_session, None)


def test_get_dashboard_no_session(mock_api_client, mock_mongo_db):
    """
    Test that GET /ui/v1/dashboard redirects when no session.
    """
    app.dependency_overrides[get_current_session] = lambda: None
    app.dependency_overrides[get_api_client] = lambda: mock_api_client
    app.dependency_overrides[get_mongo_db] = lambda: mock_mongo_db

    try:
        response = client.get("/ui/v1/dashboard")
        assert response.status_code == 302
    finally:
        app.dependency_overrides.pop(get_current_session, None)
        app.dependency_overrides.pop(get_api_client, None)
        app.dependency_overrides.pop(get_mongo_db, None)


def test_get_dashboard_with_session(mock_session_data, mock_api_client, mock_mongo_db):
    """
    Test that GET /ui/v1/dashboard renders when session exists.
    """
    app.dependency_overrides[get_current_session] = lambda: mock_session_data
    app.dependency_overrides[get_api_client] = lambda: mock_api_client
    app.dependency_overrides[get_mongo_db] = lambda: mock_mongo_db

    try:
        response = client.get("/ui/v1/dashboard")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_session, None)
        app.dependency_overrides.pop(get_api_client, None)
        app.dependency_overrides.pop(get_mongo_db, None)


def test_get_dashboard_htmx(mock_session_data, mock_api_client, mock_mongo_db):
    """
    Test that GET /ui/v1/dashboard returns partial for HTMX request.
    """
    app.dependency_overrides[get_current_session] = lambda: mock_session_data
    app.dependency_overrides[get_api_client] = lambda: mock_api_client
    app.dependency_overrides[get_mongo_db] = lambda: mock_mongo_db

    try:
        response = client.get("/ui/v1/dashboard", headers={"HX-Request": "true"})
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_session, None)
        app.dependency_overrides.pop(get_api_client, None)
        app.dependency_overrides.pop(get_mongo_db, None)


def test_get_profile_no_session():
    """
    Test that GET /ui/v1/profile redirects when no session.
    """
    app.dependency_overrides[get_current_session] = lambda: None

    try:
        response = client.get("/ui/v1/profile")
        assert response.status_code == 302
    finally:
        app.dependency_overrides.pop(get_current_session, None)


def test_get_profile_with_session(mock_session_data):
    """
    Test that GET /ui/v1/profile renders when session exists.
    """
    app.dependency_overrides[get_current_session] = lambda: mock_session_data

    try:
        response = client.get("/ui/v1/profile")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_session, None)


def test_get_settings_modal_no_session(mock_user_settings_service):
    """
    Test that GET /ui/v1/settings redirects when no session.
    """
    app.dependency_overrides[get_current_session] = lambda: None
    app.dependency_overrides[get_web_user_settings_service] = (
        lambda: mock_user_settings_service
    )

    try:
        response = client.get("/ui/v1/settings")
        assert response.status_code == 302
    finally:
        app.dependency_overrides.pop(get_current_session, None)
        app.dependency_overrides.pop(get_web_user_settings_service, None)


def test_get_settings_modal_with_session(mock_session_data, mock_user_settings_service):
    """
    Test that GET /ui/v1/settings renders when session exists.
    """
    app.dependency_overrides[get_current_session] = lambda: mock_session_data
    app.dependency_overrides[get_web_user_settings_service] = (
        lambda: mock_user_settings_service
    )

    try:
        response = client.get("/ui/v1/settings")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_session, None)
        app.dependency_overrides.pop(get_web_user_settings_service, None)


def test_get_settings_general_with_session(
    mock_session_data, mock_user_settings_service
):
    """
    Test that GET /ui/v1/settings/general renders when session exists.
    """
    app.dependency_overrides[get_current_session] = lambda: mock_session_data
    app.dependency_overrides[get_web_user_settings_service] = (
        lambda: mock_user_settings_service
    )

    try:
        response = client.get("/ui/v1/settings/general")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_session, None)
        app.dependency_overrides.pop(get_web_user_settings_service, None)


def test_post_settings_general_with_session(
    mock_session_data, mock_user_settings_service
):
    """
    Test that POST /ui/v1/settings/general saves and re-renders.
    """
    app.dependency_overrides[get_current_session] = lambda: mock_session_data
    app.dependency_overrides[get_web_user_settings_service] = (
        lambda: mock_user_settings_service
    )

    try:
        response = client.post(
            "/ui/v1/settings/general",
            data={
                "display_name": "Updated",
                "timezone": "US/Eastern",
                "page_size": "25",
            },
        )
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_session, None)
        app.dependency_overrides.pop(get_web_user_settings_service, None)


def test_get_settings_general_no_session(mock_user_settings_service):
    """
    Test that GET /ui/v1/settings/general redirects when no session.
    """
    app.dependency_overrides[get_current_session] = lambda: None
    app.dependency_overrides[get_web_user_settings_service] = (
        lambda: mock_user_settings_service
    )

    try:
        response = client.get("/ui/v1/settings/general")
        assert response.status_code == 302
    finally:
        app.dependency_overrides.pop(get_current_session, None)
        app.dependency_overrides.pop(get_web_user_settings_service, None)


def test_post_settings_general_no_session(mock_user_settings_service):
    """
    Test that POST /ui/v1/settings/general redirects when no session.
    """
    app.dependency_overrides[get_current_session] = lambda: None
    app.dependency_overrides[get_web_user_settings_service] = (
        lambda: mock_user_settings_service
    )

    try:
        response = client.post(
            "/ui/v1/settings/general",
            data={
                "display_name": "X",
                "timezone": "UTC",
                "page_size": "10",
            },
        )
        assert response.status_code == 302
    finally:
        app.dependency_overrides.pop(get_current_session, None)
        app.dependency_overrides.pop(get_web_user_settings_service, None)


def test_get_web_user_settings_service_dependency():
    """
    Test that get_web_user_settings_service returns a service instance.
    """
    svc = get_web_user_settings_service(db=MagicMock())
    assert isinstance(svc, WebUIUserSettingsService)


def test_get_dashboard_with_api_counts(mock_session_data):
    """
    Test dashboard with successful API responses for counts and display name.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []
    mock_response.headers = {"X-Total-Count": "5"}
    mock_response.text = ""

    mock_api = MagicMock()
    mock_api.get = AsyncMock(return_value=mock_response)

    mock_collection = MagicMock()
    mock_collection.find_one = AsyncMock(
        return_value={
            "id": "s1",
            "user_id": "user-123",
            "name": "display_name",
            "value": "My Name",
        }
    )
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    app.dependency_overrides[get_current_session] = lambda: mock_session_data
    app.dependency_overrides[get_api_client] = lambda: mock_api
    app.dependency_overrides[get_mongo_db] = lambda: mock_db

    try:
        response = client.get("/ui/v1/dashboard")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_session, None)
        app.dependency_overrides.pop(get_api_client, None)
        app.dependency_overrides.pop(get_mongo_db, None)


def test_get_dashboard_with_api_errors(mock_session_data):
    """
    Test dashboard when API and DB calls fail, exercising exception paths.
    """
    mock_api = MagicMock()
    mock_api.get = AsyncMock(side_effect=Exception("API unavailable"))

    mock_collection = MagicMock()
    mock_collection.find_one = AsyncMock(side_effect=Exception("DB unavailable"))
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    app.dependency_overrides[get_current_session] = lambda: mock_session_data
    app.dependency_overrides[get_api_client] = lambda: mock_api
    app.dependency_overrides[get_mongo_db] = lambda: mock_db

    try:
        response = client.get("/ui/v1/dashboard")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_session, None)
        app.dependency_overrides.pop(get_api_client, None)
        app.dependency_overrides.pop(get_mongo_db, None)
