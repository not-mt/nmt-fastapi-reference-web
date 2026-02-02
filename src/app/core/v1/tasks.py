# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Set-up and initialize async tasks engine."""

from huey import RedisExpireHuey, SqliteHuey

from app.core.v1.settings import get_app_settings

settings = get_app_settings()

huey_app = SqliteHuey(
    name=settings.tasks.name,
    filename=settings.tasks.sqlite_filename,
)

if settings.tasks.backend == "redis":
    huey_app = RedisExpireHuey(
        name=settings.tasks.name,
        url=settings.tasks.url,
    )
