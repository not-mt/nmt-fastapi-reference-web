# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Core functions for provisioning discovered services."""

import logging

from nmtfast.discovery.v1.clients import create_api_client
from nmtfast.discovery.v1.exceptions import ServiceConnectionError

from app.core.v1.cache import app_cache
from app.core.v1.settings import get_app_settings

logger = logging.getLogger(__name__)
settings = get_app_settings()
api_clients = {}  # this will be populated by create_api_clients()

# NOTE: these are names of services defined discovery section of the app config
required_clients = ["widgets"]


async def create_api_clients() -> None:
    """
    Create all API clients when the app starts.
    """
    for client_name in required_clients:
        try:
            api_clients[client_name] = await create_api_client(
                settings.auth,
                settings.discovery,
                client_name,
                cache=app_cache,
            )
        except ServiceConnectionError as exc:
            logger.critical(f"API client failure for {client_name} service: {exc}")
            for service, client in api_clients.items():
                logger.warning(f"Attempting to close {service} API client...")
                await client.aclose()
            raise

    logger.info(f"Created {len(api_clients.keys())} API client(s)")
