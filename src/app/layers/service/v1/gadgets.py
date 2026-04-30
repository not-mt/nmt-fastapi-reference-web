# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""
Business logic for gadget web UI operations.

This service acts as an intermediary between the web UI router and the
upstream gadget API repository, following the BFF (Backend for Frontend) pattern.
"""

import logging
from typing import Literal

from nmtfast.htmx.v1.schemas import PaginationMeta
from nmtfast.repositories.gadgets.v1.api import GadgetApiRepository
from nmtfast.repositories.gadgets.v1.schemas import (
    GadgetCreate,
    GadgetRead,
    GadgetUpdate,
    GadgetZap,
    GadgetZapTask,
)

logger = logging.getLogger(__name__)


class WebUIGadgetService:
    """
    Service layer for gadget CRUD operations in the web UI.

    Args:
        gadget_repository: The upstream gadget API repository.
    """

    def __init__(self, gadget_repository: GadgetApiRepository) -> None:
        self.gadget_repository: GadgetApiRepository = gadget_repository

    async def list_gadgets(
        self,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "id",
        sort_order: Literal["asc", "desc"] = "asc",
        search: str | None = None,
    ) -> tuple[list[GadgetRead], PaginationMeta]:
        """
        Retrieve gadgets from the upstream API with pagination and sorting.

        Args:
            page: The page number to retrieve (1-indexed).
            page_size: The number of items per page.
            sort_by: The field name to sort by.
            sort_order: The sort direction ('asc' or 'desc').
            search: Optional search filter string.

        Returns:
            tuple[list[GadgetRead], PaginationMeta]: Gadgets and pagination metadata.
        """
        return await self.gadget_repository.get_all(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
        )

    async def get_gadget(self, gadget_id: str) -> GadgetRead:
        """
        Retrieve a single gadget by ID from the upstream API.

        Args:
            gadget_id: The ID of the gadget to retrieve.

        Returns:
            GadgetRead: The retrieved gadget.
        """
        return await self.gadget_repository.get_by_id(gadget_id)

    async def create_gadget(self, data: GadgetCreate) -> GadgetRead:
        """
        Create a new gadget through the upstream API.

        Args:
            data: The gadget creation data.

        Returns:
            GadgetRead: The newly created gadget.
        """
        return await self.gadget_repository.gadget_create(data)

    async def update_gadget(
        self,
        gadget_id: str,
        data: GadgetUpdate,
    ) -> GadgetRead:
        """
        Update an existing gadget through the upstream API.

        Args:
            gadget_id: The ID of the gadget to update.
            data: The partial update data.

        Returns:
            GadgetRead: The updated gadget.
        """
        return await self.gadget_repository.gadget_update(gadget_id, data)

    async def delete_gadget(self, gadget_id: str) -> None:
        """
        Delete a gadget through the upstream API.

        Args:
            gadget_id: The ID of the gadget to delete.
        """
        await self.gadget_repository.gadget_delete(gadget_id)

    async def bulk_delete_gadgets(self, ids: list[str]) -> int:
        """
        Bulk delete gadgets through the upstream API.

        Args:
            ids: The list of gadget IDs to delete.

        Returns:
            int: The number of gadgets deleted.
        """
        return await self.gadget_repository.gadget_bulk_delete(ids)

    async def bulk_update_gadgets(
        self,
        ids: list[str],
        data: GadgetUpdate,
    ) -> int:
        """
        Bulk update gadgets through the upstream API.

        Args:
            ids: The list of gadget IDs to update.
            data: The partial update data to apply.

        Returns:
            int: The number of gadgets updated.
        """
        return await self.gadget_repository.gadget_bulk_update(ids, data)

    async def zap_gadget(
        self,
        gadget_id: str,
        payload: GadgetZap,
    ) -> GadgetZapTask:
        """
        Initiate a zap operation on a gadget.

        Args:
            gadget_id: The ID of the gadget to zap.
            payload: The zap configuration.

        Returns:
            GadgetZapTask: Status details about the newly created task.
        """
        return await self.gadget_repository.gadget_zap(gadget_id, payload)

    async def get_zap_status(
        self,
        gadget_id: str,
        task_uuid: str,
    ) -> GadgetZapTask:
        """
        Retrieve the status of a zap task.

        Args:
            gadget_id: The ID of the gadget being zapped.
            task_uuid: The UUID of the zap task.

        Returns:
            GadgetZapTask: Status details about the task.
        """
        return await self.gadget_repository.gadget_zap_by_uuid(gadget_id, task_uuid)
