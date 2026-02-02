# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Dependencies related to caching."""

from fastapi import Depends
from nmtfast.cache.v1.base import AppCacheBase

from app.core.v1.cache import app_cache
from app.core.v1.settings import AppSettings, get_app_settings


async def get_cache(
    settings: AppSettings = Depends(get_app_settings),
) -> AppCacheBase:
    """
    Provide an application caching object.

    This provides dependency injection of app_cache objects into the dependency graph.

    Args:
        settings: The application settings.

    Returns:
        AppCacheBase: An implementation of the super class.
    """
    return app_cache
