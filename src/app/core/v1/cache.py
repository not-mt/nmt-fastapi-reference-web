# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Set-up and initialize caching."""

from nmtfast.cache.v1.huey import HueyAppCache

from app.core.v1.settings import get_app_settings
from app.core.v1.tasks import huey_app

settings = get_app_settings()

app_cache = HueyAppCache(
    huey_app=huey_app,
    name=settings.cache.name,
    default_ttl=settings.cache.ttl,
)


# TODO: add support for MongoDB


# def get_app_cache() -> AppCacheBase:
#     """
#     Dependency function to provide app_cache object.
#
#     Returns:
#         AppCacheBase: The app_cache object, an implementation of AppCacheBase.
#     """
#     return app_cache
