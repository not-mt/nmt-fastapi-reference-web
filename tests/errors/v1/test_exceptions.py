# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for exceptions."""

from app.errors.v1.exceptions import ResourceNotFoundError


def test_not_found_error_initialization():
    """Tests the initialization of the ResourceNotFoundError."""

    resource_id = "123"
    resource_name = "Widget"
    error = ResourceNotFoundError(resource_id, resource_name)

    assert error.resource_id == resource_id
    assert error.resource_name == resource_name
    assert str(error) == "Widget with ID 123 not found."


def test_not_found_error_int_id():
    """Tests the initialization of the ResourceNotFoundError with an integer resource ID."""

    resource_id = 456
    resource_name = "Item"
    error = ResourceNotFoundError(resource_id, resource_name)

    assert error.resource_id == resource_id
    assert error.resource_name == resource_name
    assert str(error) == "Item with ID 456 not found."


def test_not_found_error_string_id():
    """Tests the initialization of the ResourceNotFoundError with a string resource ID."""

    resource_id = "abc-def"
    resource_name = "Product"
    error = ResourceNotFoundError(resource_id, resource_name)

    assert error.resource_id == resource_id
    assert error.resource_name == resource_name
    assert str(error) == "Product with ID abc-def not found."
