# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Business logic for Web UI operations."""

import logging
from typing import Optional

from aiokafka import AIOKafkaProducer
from nmtfast.auth.v1.acl import check_acl
from nmtfast.cache.v1.base import AppCacheBase

from app.core.v1.settings import AppSettings

# from app.layers.repository.v1.widgets import WidgetRepository
# from app.schemas.dto.v1.widgets import (
#     WidgetCreate,
#     WidgetRead,
#     WidgetZap,
#     WidgetZapTask,
# )

logger = logging.getLogger(__name__)


class WebUIService:
    """
    Service layer for web UI operations.

    Args:
        acls: List of ACLs associated with authenticated client/apikey.
        settings: The application's AppSettings object.
        cache: An implementation of AppCacheBase, for getting/setting cached data.
        kafka: Optional Kafka producer, if enabled in configuration.
    """

    def __init__(
        self,
        # widget_repository: WidgetRepository,
        acls: list,
        settings: AppSettings,
        cache: AppCacheBase,
        kafka: Optional[AIOKafkaProducer],
    ) -> None:
        # self.widget_repository: WidgetRepository = widget_repository
        self.acls = acls
        self.settings = settings
        self.cache = cache
        self.kafka = kafka

    async def _is_authz(self, acls: list, permission: str) -> None:
        """
        Check if the ACLs allow access to the given resource.

        Args:
            acls: List of ACLs associated with this client
            permission: Required in order to complete the requested operation.
        """
        # TODO: check whether user is even authenticated before checking ACLs
        #   if not authenticated, raise NotAuthenticatedError instead of
        #   AuthorizationError

        # NOTE: by default, check_acl now raises AuthorizationError on failure
        await check_acl("index", acls, permission)

    async def dummy_index(self) -> None:
        """
        Dummy index method to demonstrate service layer structure.

        Returns:
            None: This function returns nothing.
        """
        # await self._is_authz(self.acls, "view")
        # db_widget = await self.widget_repository.widget_create(input_widget)

        return None
