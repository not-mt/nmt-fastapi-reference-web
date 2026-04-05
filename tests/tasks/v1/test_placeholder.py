# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Tests for placeholder task."""

from app.tasks.v1.placeholder import placeholder_task


def test_placeholder_task_returns_ok():
    """
    Test that placeholder_task returns 'ok'.
    """
    result = placeholder_task.call_local()
    assert result == "ok"
