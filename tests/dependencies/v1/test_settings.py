# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for settings dependency injection functions."""

import pytest

from app.dependencies.v1.settings import AppSettings, get_settings


@pytest.mark.asyncio
async def test_widget_create_success():
    """Test fetching settings using get_settings()."""

    settings: AppSettings = await get_settings()

    assert hasattr(settings, "version")
