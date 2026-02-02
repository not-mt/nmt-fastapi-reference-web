# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for exception handlers."""

import json
from unittest.mock import MagicMock

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from nmtfast.auth.v1.exceptions import AuthorizationError
from nmtfast.errors.v1.exceptions import (
    BaseUpstreamRepositoryException,
    UpstreamApiException,
)

from app.errors.v1.exception_handlers import (
    authorization_error_handler,
    generic_not_found_error_handler,
    index_out_of_range_error_handler,
    resource_not_found_error_handler,
    server_error_handler,
    upstream_api_exception_handler,
)


def test_generic_not_found_error_handler():
    """
    Test generic_not_found_error_handler.
    """
    request = MagicMock(spec=Request)
    exc = HTTPException(status_code=404)
    response = generic_not_found_error_handler(request, exc)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 404
    assert json.loads(response.body) == {"message": "Not Found"}


def test_resource_not_found_error_handler():
    """
    Test resource_not_found_error_handler.
    """
    request = MagicMock(spec=Request)
    exc = HTTPException(status_code=404)
    response = resource_not_found_error_handler(request, exc)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 404
    assert json.loads(response.body) == {"message": "404: Not Found"}


def test_server_error_handler():
    """
    Test server_error_handler.
    """
    request = MagicMock(spec=Request)
    exc = HTTPException(status_code=500)
    response = server_error_handler(request, exc)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 500
    assert json.loads(response.body) == {"message": "Internal Server Error"}


def test_index_out_of_range_error_handler():
    """
    Test index_out_of_range_error_handler.
    """
    request = MagicMock(spec=Request)
    exc = IndexError("Test index error")
    response = index_out_of_range_error_handler(request, exc)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 400
    assert json.loads(response.body) == {"message": "Index out of range"}


def test_upstream_api_exception_handler():
    """
    Test upstream_api_exception_handler.
    """

    # create a mock repository exception
    class MockRepoException(BaseUpstreamRepositoryException):
        def __init__(self):
            self.status_code = 503
            self.message = "Service unavailable"
            self.req_id = "req-123"

    request = MagicMock(spec=Request)
    repo_exc = MockRepoException()
    exc = UpstreamApiException(repo_exc)

    response = upstream_api_exception_handler(request, exc)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 502
    assert json.loads(response.body) == {
        "error": "upstream_api_failure",
        "status_code": 503,
        "message": "Service unavailable",
        "request_id": "req-123",
    }


def test_authorization_error_handler():
    """
    Test AuthorizationError handler.
    """
    request = MagicMock(spec=Request)
    exc = AuthorizationError("Test authorization error")
    response = authorization_error_handler(request, exc)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 403
    assert json.loads(response.body) == {"message": "Test authorization error"}
