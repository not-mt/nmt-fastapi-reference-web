# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""This module defines API endpoints for health/readiness checks."""

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from nmtfast.cache.v1.base import AppCacheBase
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.v1.health import check_app_readiness
from app.core.v1.settings import AppSettings
from app.dependencies.v1.cache import get_cache
from app.dependencies.v1.settings import get_settings
from app.dependencies.v1.sqlalchemy import get_sql_db
from app.layers.repository.v1.widgets import WidgetRepository
from app.layers.service.v1.health import AppHealthService

logger = logging.getLogger(__name__)
health_router = APIRouter(
    # prefix="/health",
    tags=["API Health Operations"],
)


def get_health_service(
    settings: AppSettings = Depends(get_settings),
    db: AsyncSession = Depends(get_sql_db),
    cache: AppCacheBase = Depends(get_cache),
) -> AppHealthService:
    """
    Dependency function to provide a ApphealthService instance.

    Args:
        settings: The application's AppSettings object.
        db: The asynchronous MongoDB database.
        cache: An implementation of AppCacheBase, for getting/setting cache data.

    Returns:
        AppHealthService: An instance of the app health service.
    """
    widget_repository = WidgetRepository(db)

    return AppHealthService(settings, widget_repository, cache)


@health_router.get(
    path="/health/liveness",
    include_in_schema=False,
)
async def liveness(
    health_service: AppHealthService = Depends(get_health_service),
) -> JSONResponse:
    """
    Perform liveness check(s) to determine if application is alive.

    This check similar to the readiness check, but it will NOT call
    check_app_readiness() to see if the app is in the process of shutting down,
    and it will not bother checking database and cache availability.

    Args:
        health_service: The app health service instance.

    Returns:
        JSONResponse: The retrieved readiness information.
    """
    healthy = await health_service.check_health(checks=["basic"])
    if not healthy:
        return JSONResponse(
            status_code=503, content={"status": "dependencies not ready"}
        )

    return JSONResponse({"status": "alive"})


@health_router.get(
    path="/health/readiness",
    include_in_schema=False,
)
async def readiness(
    health_service: AppHealthService = Depends(get_health_service),
) -> JSONResponse:
    """
    Perform readiness check(s) to determine if application is ready for requests.

    check_app_readiness() is called first to make sure that the app is not currently
    being shut down (after receiving SIGTERM). After that, critical dependencies are
    checked to determine if all of them are working; e.g. database connectivity is
    critical to the core function of the application, so the app would not be
    considered ready if it is cannot communicate with the database.

    Args:
        health_service: The app health service instance.

    Returns:
        JSONResponse: The retrieved readiness information.
    """
    if not check_app_readiness():
        return JSONResponse(status_code=503, content={"status": "not ready"})

    healthy = await health_service.check_health(
        checks=["basic", "database", "cache"],
    )
    if not healthy:
        return JSONResponse(
            status_code=503, content={"status": "dependencies not ready"}
        )

    return JSONResponse({"status": "ready"})
