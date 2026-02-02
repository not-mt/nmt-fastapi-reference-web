# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Business logic to check health of service dependencies."""

import json
import logging

from nmtfast.cache.v1.base import AppCacheBase
from sqlalchemy import text

from app.core.v1.settings import AppSettings
from app.layers.repository.v1.widgets import WidgetRepository

logger = logging.getLogger(__name__)


class AppHealthService:
    """
    Service layer for application health checks.

    Args:
        settings: The application's AppSettings object.
        widget_repository: The repository for widget data operations.
        cache: An implementation of AppCacheBase, for getting/setting cached data.
    """

    def __init__(
        self,
        settings: AppSettings,
        widget_repository: WidgetRepository,
        cache: AppCacheBase,
    ) -> None:
        self.settings = settings
        self.widget_repository: WidgetRepository = widget_repository
        self.cache = cache

    async def _check_database(self) -> bool:
        """
        Check if app database connection is alive/ready.

        Returns:
            bool: Whether the readiness check(s) passed or not.

        Raises:
            Exception: Raises an exception if unable to communicate with DB.
        """
        try:
            await self.widget_repository.db.execute(text("SELECT 1"))
            logger.debug("Database health check passed")
        except Exception:
            logger.critical("Database health check failed!", exc_info=True)
            raise
        return True

    async def _check_cache(self) -> bool:
        """
        Check if app cache connection is alive/ready.

        Returns:
            bool: Whether the readiness check(s) passed or not.

        Raises:
            Exception: Raises an exception if unable to communicate with cache.
        """
        try:
            self.cache.store_app_cache("app_cache_health", json.dumps("HEALTHY"))
            if raw_value := self.cache.fetch_app_cache("app_cache_health"):
                cache_str = json.loads(raw_value.decode("utf-8"))
                if cache_str != "HEALTHY":
                    raise Exception(f"Cache health check failed! Result: {cache_str}")
            logger.debug("Cache health check passed")
        except Exception:
            logger.critical("Cache health check failed!", exc_info=True)
            raise
        return True

    async def check_health(self, checks: list[str] = ["basic"]) -> bool:
        """
        Check if app is ready.

        Args:
            checks: A list of checks to perform.

        Returns:
            bool: Whether the readiness check(s) passed or not.
        """
        results: dict[str, bool] = {}

        if "basic" in checks:
            results["basic"] = True

        if "database" in checks:
            try:
                results["database"] = await self._check_database()
            except Exception:
                logger.critical("Database health check failed!", exc_info=True)
                results["database"] = False

        if "cache" in checks:
            try:
                results["cache"] = await self._check_cache()
            except Exception:
                logger.critical("Cache health check failed!", exc_info=True)
                results["cache"] = False

        for value in results.values():
            if value is False:
                return False

        return True
