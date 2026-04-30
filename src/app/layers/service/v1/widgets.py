# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""
Business logic for widget web UI operations.

This service acts as an intermediary between the web UI router and the
upstream widget API repository, following the BFF (Backend for Frontend) pattern.
"""

import logging
from typing import Literal

from nmtfast.htmx.v1.schemas import PaginationMeta
from nmtfast.repositories.widgets.v1.api import WidgetApiRepository
from nmtfast.repositories.widgets.v1.schemas import (
    WidgetCreate,
    WidgetRead,
    WidgetUpdate,
    WidgetZap,
    WidgetZapTask,
)

logger = logging.getLogger(__name__)


class WebUIWidgetService:
    """
    Service layer for widget CRUD operations in the web UI.

    Args:
        widget_repository: The upstream widget API repository.
    """

    def __init__(self, widget_repository: WidgetApiRepository) -> None:
        self.widget_repository: WidgetApiRepository = widget_repository

    async def list_widgets(
        self,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "id",
        sort_order: Literal["asc", "desc"] = "asc",
        search: str | None = None,
    ) -> tuple[list[WidgetRead], PaginationMeta]:
        """
        Retrieve widgets from the upstream API with pagination and sorting.

        Args:
            page: The page number to retrieve (1-indexed).
            page_size: The number of items per page.
            sort_by: The field name to sort by.
            sort_order: The sort direction ('asc' or 'desc').
            search: Optional search filter string.

        Returns:
            tuple[list[WidgetRead], PaginationMeta]: Widgets and pagination metadata.
        """
        return await self.widget_repository.get_all(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
        )

    async def get_widget(self, widget_id: int) -> WidgetRead:
        """
        Retrieve a single widget by ID from the upstream API.

        Args:
            widget_id: The ID of the widget to retrieve.

        Returns:
            WidgetRead: The retrieved widget.
        """
        return await self.widget_repository.get_by_id(widget_id)

    async def create_widget(self, data: WidgetCreate) -> WidgetRead:
        """
        Create a new widget through the upstream API.

        Args:
            data: The widget creation data.

        Returns:
            WidgetRead: The newly created widget.
        """
        return await self.widget_repository.widget_create(data)

    async def update_widget(
        self,
        widget_id: int,
        data: WidgetUpdate,
    ) -> WidgetRead:
        """
        Update an existing widget through the upstream API.

        Args:
            widget_id: The ID of the widget to update.
            data: The partial update data.

        Returns:
            WidgetRead: The updated widget.
        """
        return await self.widget_repository.widget_update(widget_id, data)

    async def delete_widget(self, widget_id: int) -> None:
        """
        Delete a widget through the upstream API.

        Args:
            widget_id: The ID of the widget to delete.
        """
        await self.widget_repository.widget_delete(widget_id)

    async def bulk_delete_widgets(self, ids: list[int]) -> int:
        """
        Bulk delete widgets through the upstream API.

        Args:
            ids: The list of widget IDs to delete.

        Returns:
            int: The number of widgets deleted.
        """
        return await self.widget_repository.widget_bulk_delete(ids)

    async def bulk_update_widgets(
        self,
        ids: list[int],
        data: WidgetUpdate,
    ) -> int:
        """
        Bulk update widgets through the upstream API.

        Args:
            ids: The list of widget IDs to update.
            data: The partial update data to apply.

        Returns:
            int: The number of widgets updated.
        """
        return await self.widget_repository.widget_bulk_update(ids, data)

    async def zap_widget(
        self,
        widget_id: int,
        payload: WidgetZap,
    ) -> WidgetZapTask:
        """
        Initiate a zap operation on a widget.

        Args:
            widget_id: The ID of the widget to zap.
            payload: The zap configuration.

        Returns:
            WidgetZapTask: Status details about the newly created task.
        """
        return await self.widget_repository.widget_zap(widget_id, payload)

    async def get_zap_status(
        self,
        widget_id: int,
        task_uuid: str,
    ) -> WidgetZapTask:
        """
        Retrieve the status of a zap task.

        Args:
            widget_id: The ID of the widget being zapped.
            task_uuid: The UUID of the zap task.

        Returns:
            WidgetZapTask: Status details about the task.
        """
        return await self.widget_repository.widget_zap_by_uuid(widget_id, task_uuid)
