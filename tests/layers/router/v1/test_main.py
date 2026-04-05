# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for webui router layer."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from nmtfast.auth.v1.sessions import SessionData

from app.core.v1.settings import AppSettings
from app.dependencies.v1.session import get_current_session
from app.layers.router.v1.main import get_webui_service
from app.layers.service.v1.main import WebUIService
from app.main import app

client = TestClient(app, follow_redirects=False)


@pytest.fixture
def mock_webui_service():
    """
    Fixture to provide a mock WebUIService.
    """
    svc = AsyncMock(spec=WebUIService)
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
    return session


def test_get_index_redirects_when_no_session(mock_webui_service):
    """
    Test that GET /ui/v1 redirects to login when no session exists.
    """
    app.dependency_overrides[get_webui_service] = lambda: mock_webui_service
    app.dependency_overrides[get_current_session] = lambda: None

    try:
        response = client.get("/ui/v1")
        assert response.status_code == 302
        assert response.headers["location"] == "/ui/v1/login"
    finally:
        app.dependency_overrides.pop(get_webui_service, None)
        app.dependency_overrides.pop(get_current_session, None)


def test_get_index_renders_when_session_exists(mock_webui_service, mock_session_data):
    """
    Test that GET /ui/v1 renders the index page when a session exists.
    """
    app.dependency_overrides[get_webui_service] = lambda: mock_webui_service
    app.dependency_overrides[get_current_session] = lambda: mock_session_data

    try:
        response = client.get("/ui/v1")
        assert response.status_code == 200
        mock_webui_service.dummy_index.assert_awaited_once()
    finally:
        app.dependency_overrides.pop(get_webui_service, None)
        app.dependency_overrides.pop(get_current_session, None)


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
