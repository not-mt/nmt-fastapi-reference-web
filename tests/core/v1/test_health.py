# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for core readiness functions."""

from app.core.v1 import health
from app.core.v1.health import (
    check_app_readiness,
    set_app_not_ready,
    set_app_ready,
)


def test_app_initial_readiness_state():
    """
    Test that the app readiness state is initially False.
    """
    # Reset the state in case other tests modify it
    health.is_ready = False

    assert check_app_readiness() is False


def test_set_app_ready():
    """
    Test set_app_ready sets readiness to True.
    """
    health.is_ready = False
    set_app_ready()

    assert check_app_readiness() is True


def test_set_app_not_ready():
    """
    Test set_app_not_ready sets readiness to False.
    """
    health.is_ready = True
    set_app_not_ready()

    assert check_app_readiness() is False
