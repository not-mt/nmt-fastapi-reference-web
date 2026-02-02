# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Dependencies related to settings and config options."""

from app.core.v1.settings import AppSettings, get_app_settings


async def get_settings() -> AppSettings:
    """
    Dependency function to provide settings.
    """
    return get_app_settings()
