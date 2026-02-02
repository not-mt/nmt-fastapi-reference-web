# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Business logic for widget API resources."""

import logging

from nmtfast.auth.v1.acl import check_acl
from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.errors.v1.exceptions import UpstreamApiException
from nmtfast.repositories.widgets.v1.api import WidgetApiRepository
from nmtfast.repositories.widgets.v1.exceptions import WidgetApiException
from nmtfast.repositories.widgets.v1.schemas import (
    WidgetCreate,
    WidgetRead,
    WidgetZap,
    WidgetZapTask,
)

from app.core.v1.settings import AppSettings

logger = logging.getLogger(__name__)


class WidgetApiService:
    """
    Service layer for widget business logic.

    Args:
        widget_api_repository: The API repository for widget data operations.
        acls: List of ACLs associated with authenticated client/apikey.
        settings: The application's AppSettings object.
        cache: An implementation of AppCacheBase, for getting/setting cached data.
    """

    def __init__(
        self,
        widget_api_repository: WidgetApiRepository,
        acls: list,
        settings: AppSettings,
        cache: AppCacheBase,
    ) -> None:
        self.widget_api_repository: WidgetApiRepository = widget_api_repository
        self.acls = acls
        self.settings = settings
        self.cache = cache

    async def _is_authz(self, acls: list, permission: str) -> None:
        """
        Check if the ACLs allow access to the given resource.

        Args:
            acls: List of ACLs associated with this client
            permission: Required in order to complete the requested operation.
        """
        # NOTE: by default, check_acl now raises AuthorizationError on failure
        await check_acl("widgets", acls, permission)

    async def widget_create(self, input_widget: WidgetCreate) -> WidgetRead:
        """
        Create a new widget.

        Args:
            input_widget: The widget data provided by the client.

        Returns:
            WidgetRead: The newly created widget as a Pydantic model.

        Raises:
            UpstreamApiException: Raised if an upstream API error is reported.
        """
        await self._is_authz(self.acls, "create")

        try:
            api_widget = await self.widget_api_repository.widget_create(input_widget)
        except WidgetApiException as exc:
            raise UpstreamApiException(exc)

        return WidgetRead.model_validate(api_widget)

    async def widget_get_by_id(self, widget_id: int, repo: str = "db") -> WidgetRead:
        """
        Retrieve a widget by its ID.

        Args:
            widget_id: The ID of the widget to retrieve.
            repo: The repository from which to retrieve the resource.

        Raises:
            UpstreamApiException: Raised if an upstream API error is reported.

        Returns:
            WidgetRead: The retrieved widget.
        """
        await self._is_authz(self.acls, "read")

        try:
            api_widget = await self.widget_api_repository.get_by_id(widget_id)
        except WidgetApiException as exc:
            raise UpstreamApiException(exc)

        return WidgetRead.model_validate(api_widget)

    async def widget_zap(self, widget_id: int, payload: WidgetZap) -> WidgetZapTask:
        """
        Zap an existing widget.

        Args:
            widget_id: The ID of the widget to zap.
            payload: Parameters for the async task.

        Raises:
            UpstreamApiException: Raised if an upstream API error is reported.

        Returns:
            WidgetZapTask: Information about the newly created task.
        """
        await self._is_authz(self.acls, "zap")

        try:
            zap_task = await self.widget_api_repository.widget_zap(widget_id, payload)
        except WidgetApiException as exc:
            raise UpstreamApiException(exc)

        return WidgetZapTask.model_validate(zap_task)

    async def widget_zap_by_uuid(
        self,
        widget_id: int,
        task_uuid: str,
    ) -> WidgetZapTask:
        """
        Retrieve a widget by its ID.

        Args:
            widget_id: The ID of the widget.
            task_uuid: The UUID of the async task.

        Raises:
            UpstreamApiException: Raised if an upstream API error is reported.

        Returns:
            WidgetZapTask: The retrieved widget.
        """
        await self._is_authz(self.acls, "read")

        try:
            zap_task = await self.widget_api_repository.widget_zap_by_uuid(
                widget_id, task_uuid
            )
        except WidgetApiException as exc:
            raise UpstreamApiException(exc)

        return WidgetZapTask.model_validate(zap_task)
