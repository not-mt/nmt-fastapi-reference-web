# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Business logic for gadget resources."""

import logging

from nmtfast.auth.v1.acl import check_acl
from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.middleware.v1.request_id import REQUEST_ID_CONTEXTVAR
from nmtfast.tasks.v1.huey import (
    fetch_task_metadata,
    fetch_task_result,
    store_task_metadata,
)

from app.core.v1.settings import AppSettings
from app.core.v1.tasks import huey_app
from app.errors.v1.exceptions import ResourceNotFoundError
from app.layers.repository.v1.gadgets import GadgetRepository
from app.schemas.dto.v1.gadgets import (
    GadgetCreate,
    GadgetRead,
    GadgetZap,
    GadgetZapTask,
)
from app.tasks.v1.gadgets import GadgetZapParams, gadget_zap_task

logger = logging.getLogger(__name__)


class GadgetService:
    """
    Service layer for gadget business logic.

    Args:
        gadget_repository: The repository for gadget data operations.
        acls: List of ACLs associated with authenticated client/apikey.
        settings: The application's AppSettings object.
        cache: An implementation of AppCacheBase, for getting/setting cached data.
    """

    def __init__(
        self,
        gadget_repository: GadgetRepository,
        acls: list,
        settings: AppSettings,
        cache: AppCacheBase,
    ) -> None:
        self.gadget_repository: GadgetRepository = gadget_repository
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
        await check_acl("gadgets", acls, permission)

    async def gadget_create(self, input_gadget: GadgetCreate) -> GadgetRead:
        """
        Create a new gadget.

        Args:
            input_gadget: The gadget data provided by the client.

        Returns:
            GadgetRead: The newly created gadget as a Pydantic model.
        """
        await self._is_authz(self.acls, "create")
        db_gadget = await self.gadget_repository.gadget_create(input_gadget)

        return GadgetRead.model_validate(db_gadget)

    async def gadget_get_by_id(self, gadget_id: str) -> GadgetRead:
        """
        Retrieve a gadget by its ID.

        Args:
            gadget_id: The ID of the gadget to retrieve.

        Returns:
            GadgetRead: The retrieved gadget.
        """
        await self._is_authz(self.acls, "read")
        db_gadget = await self.gadget_repository.get_by_id(gadget_id)

        return GadgetRead.model_validate(db_gadget)

    async def gadget_zap(self, gadget_id: str, payload: GadgetZap) -> GadgetZapTask:
        """
        Zap an existing gadget.

        Args:
            gadget_id: The ID of the gadget to zap.
            payload: Parameters for the async task.

        Returns:
            GadgetZapTask: Information about the newly created task.
        """
        await self._is_authz(self.acls, "zap")

        db_gadget = await self.gadget_repository.get_by_id(gadget_id)
        logger.debug(f"Preparing to zap gadget ID {db_gadget.id}")

        # start the async task and report the uuid
        result = gadget_zap_task(
            GadgetZapParams(
                request_id=REQUEST_ID_CONTEXTVAR.get() or "UNKNOWN",
                gadget_id=gadget_id,
                duration=payload.duration,
            )
        )
        task_uuid = "PENDING"
        # if hasattr(result, "task"):
        task = getattr(result, "task")
        task_uuid = getattr(task, "id")

        task_md = {
            "uuid": task_uuid,
            "id": gadget_id,
            "state": "PENDING",
            "duration": payload.duration,
            "runtime": 0,
        }
        store_task_metadata(huey_app, task_uuid, task_md)

        return GadgetZapTask.model_validate(task_md)

    async def gadget_zap_by_uuid(
        self,
        gadget_id: str,
        task_uuid: str,
    ) -> GadgetZapTask:
        """
        Retrieve a gadget by its ID.

        Args:
            gadget_id: The ID of the gadget.
            task_uuid: The UUID of the async task.

        Returns:
            GadgetZapTask: The retrieved gadget.

        Raises:
            ResourceNotFoundError: If the gadget is not found.
        """
        await self._is_authz(self.acls, "read")

        db_gadget = await self.gadget_repository.get_by_id(gadget_id)
        logger.debug(f"Fetching zap status for gadget ID {db_gadget.id}")

        # NOTE: missing result might mean the task is still running
        task_result = fetch_task_result(huey_app, task_uuid)
        if task_result:
            return GadgetZapTask.model_validate(task_result)

        # no result and no running metadata is a problem
        task_md = fetch_task_metadata(huey_app, task_uuid)
        if not task_result and not task_md:
            logger.debug(f"Task metadata not found for {task_uuid}")
            raise ResourceNotFoundError(task_uuid, "Task")

        return GadgetZapTask.model_validate(task_md)
