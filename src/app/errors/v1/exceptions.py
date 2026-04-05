# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""API-specific exceptions for resources."""


class ResourceNotFoundError(Exception):
    """
    Initializes the RepoResourceNotFoundError with the resource details.

    Args:
        resource_id: The ID of the resource.
        resource_name: The name of the resource (e.g., 'Widget').
    """

    def __init__(self, resource_id: str | int, resource_name: str) -> None:
        super().__init__(f"{resource_name} with ID {resource_id} not found.")
        self.resource_id: str | int = resource_id
        self.resource_name: str = resource_name


class NotAuthenticatedError(Exception):
    """
    Raised when a user is not authenticated.
    """

    pass


class LoginConfigurationError(Exception):
    """
    Raised when web authentication is not configured.
    """


class LoginStateError(Exception):
    """
    Raised when the CSRF state is invalid or expired.
    """


class LoginCodeExchangeError(Exception):
    """
    Raised when the authorization code exchange fails.
    """


class LoginTokenError(Exception):
    """
    Raised when token validation fails.
    """


class LoginClaimsError(Exception):
    """
    Raised when required claims cannot be extracted from the token.
    """
