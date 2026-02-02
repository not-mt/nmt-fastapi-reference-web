# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""
Exception handlers for widget API operations.

This module provides custom exception handlers for FastAPI applications.
It ensures consistent error responses for widget-related exceptions
and common server-side errors.
"""


from fastapi import Request
from fastapi.responses import JSONResponse
from nmtfast.errors.v1.exceptions import UpstreamApiException


def generic_not_found_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle generic 404 HTTP exceptions.

    Args:
        request: The incoming HTTP request.
        exc: The raised HTTPException with status 404.

    Returns:
        JSONResponse: A 404 response with a generic error message.
    """
    return JSONResponse(
        status_code=404,
        content={"message": "Not Found"},
    )


def resource_not_found_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle generic 404 HTTP exceptions when a resource could not be found.

    Args:
        request: The incoming HTTP request.
        exc: The raised HTTPException with status 404.

    Returns:
        JSONResponse: A 404 response with a generic error message.
    """
    return JSONResponse(
        status_code=404,
        content={"message": f"{exc}"},
    )


def server_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle generic 500 HTTP exceptions.

    Args:
        request: The incoming HTTP request.
        exc: The raised HTTPException with status 500.

    Returns:
        JSONResponse: A 500 response with a generic error message.
    """
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error"},
    )


def index_out_of_range_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle IndexError exceptions.

    Args:
        request: The incoming HTTP request.
        exc: The raised IndexError exception.

    Returns:
        JSONResponse: A 400 response indicating an invalid index access.
    """
    return JSONResponse(
        status_code=400,
        content={"message": "Index out of range"},
    )


def upstream_api_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle UpstreamApiException exceptions.

    Args:
        request: The incoming HTTP request.
        exc: The raised exception.

    Returns:
        JSONResponse: A response with details about an upstream API failure.
    """
    assert isinstance(exc, UpstreamApiException), "Wrong exception type"
    return JSONResponse(
        status_code=exc.caller_status_code,
        content={
            "error": "upstream_api_failure",
            "status_code": exc.status_code,
            "message": exc.message,
            "request_id": exc.req_id,
        },
    )


def authorization_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle AuthorizationError exceptions.

    Args:
        request: The incoming HTTP request.
        exc: The raised IndexError exception.

    Returns:
        JSONResponse: A 403 response indicating an authorization failure.
    """
    return JSONResponse(
        status_code=403,
        content={"message": f"{exc}"},
    )
