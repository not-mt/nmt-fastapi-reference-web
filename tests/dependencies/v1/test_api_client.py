# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for api_client dependency."""

from unittest.mock import MagicMock, patch

import httpx

from app.dependencies.v1.api_client import get_api_client


def _make_mock_settings() -> MagicMock:
    """
    Create a mock AppSettings with upstream reference API URL.
    """
    settings = MagicMock()
    settings.upstream.reference_api.url = "http://api.test"
    return settings


def _make_mock_session() -> MagicMock:
    """
    Create a mock SessionData with access_token.
    """
    session = MagicMock()
    session.access_token = "test-token"
    return session


def test_get_api_client_with_session_token():
    """
    Test that api client includes Authorization header when session has token.
    """
    settings = _make_mock_settings()
    session = _make_mock_session()

    client = get_api_client(settings=settings, session=session)

    assert isinstance(client, httpx.AsyncClient)
    assert client.headers.get("authorization") == "Bearer test-token"


def test_get_api_client_without_session():
    """
    Test that api client has no Authorization header when no session.
    """
    settings = _make_mock_settings()

    client = get_api_client(settings=settings, session=None)

    assert isinstance(client, httpx.AsyncClient)
    assert "authorization" not in client.headers


def test_get_api_client_with_request_id():
    """
    Test that api client forwards request ID header when set.
    """
    settings = _make_mock_settings()

    with patch("app.dependencies.v1.api_client.REQUEST_ID_CONTEXTVAR") as mock_ctx:
        mock_ctx.get.return_value = "req-123"
        client = get_api_client(settings=settings, session=None)

    assert client.headers.get("x-nmtfast-request-id") == "req-123"
