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
