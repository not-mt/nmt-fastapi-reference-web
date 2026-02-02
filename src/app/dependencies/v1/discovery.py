# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Dependencies for upstream and service-to-service API communication."""

import logging

from fastapi import Depends

from app.core.v1.discovery import api_clients
from app.core.v1.settings import AppSettings, get_app_settings

logger = logging.getLogger(__name__)
settings = get_app_settings()


async def get_api_clients(
    settings: AppSettings = Depends(get_app_settings),
) -> dict:
    """
    Provides a dictionary of async httpx clients.

    This returns httpx clients that can be used to communicate with an upstream
    API. The clients will have been configured during application startup, and can be
    acquired from this function during dependency injection.

    Args:
        settings: The application settings.

    Returns:
        dict: A dictionary of async httpx clients.
    """
    return api_clients
