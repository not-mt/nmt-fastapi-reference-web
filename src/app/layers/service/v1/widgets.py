# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Business logic for widget resources."""

import logging
from typing import Optional

from aiokafka import AIOKafkaProducer
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
from app.layers.repository.v1.widgets import WidgetRepository
from app.schemas.dto.v1.widgets import (
    WidgetCreate,
    WidgetRead,
    WidgetZap,
    WidgetZapTask,
)
from app.tasks.v1.widgets import WidgetZapParams, widget_zap_task

logger = logging.getLogger(__name__)


class WidgetService:
    """
    Service layer for widget business logic.

    Args:
        widget_repository: The repository for widget data operations.
        acls: List of ACLs associated with authenticated client/apikey.
        settings: The application's AppSettings object.
        cache: An implementation of AppCacheBase, for getting/setting cached data.
        kafka: Optional Kafka producer, if enabled in configuration.
    """

    def __init__(
        self,
        widget_repository: WidgetRepository,
        acls: list,
        settings: AppSettings,
        cache: AppCacheBase,
        kafka: Optional[AIOKafkaProducer],
    ) -> None:
        self.widget_repository: WidgetRepository = widget_repository
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
        # NOTE: by default, check_acl now raises AuthorizationError on failure
        await check_acl("widgets", acls, permission)

    async def widget_create(self, input_widget: WidgetCreate) -> WidgetRead:
        """
        Create a new widget.

        Args:
            input_widget: The widget data provided by the client.

        Returns:
            WidgetRead: The newly created widget as a Pydantic model.
        """
        await self._is_authz(self.acls, "create")
        db_widget = await self.widget_repository.widget_create(input_widget)

        # NOTE: this is a demonstration of publishing Kafka messages
        if self.settings.kafka.enabled:
            assert isinstance(self.kafka, AIOKafkaProducer)
            await self.kafka.send(
                topic="nmtfast-widgets",
                key="create-widget",
                value=WidgetRead.model_validate(db_widget),
            )

        return WidgetRead.model_validate(db_widget)

    async def widget_get_by_id(self, widget_id: int) -> WidgetRead:
        """
        Retrieve a widget by its ID.

        Args:
            widget_id: The ID of the widget to retrieve.

        Returns:
            WidgetRead: The retrieved widget.
        """
        await self._is_authz(self.acls, "read")
        db_widget = await self.widget_repository.get_by_id(widget_id)

        return WidgetRead.model_validate(db_widget)

    async def widget_zap(self, widget_id: int, payload: WidgetZap) -> WidgetZapTask:
        """
        Zap an existing widget.

        Args:
            widget_id: The ID of the widget to zap.
            payload: Parameters for the async task.

        Returns:
            WidgetZapTask: Information about the newly created task.
        """
        await self._is_authz(self.acls, "zap")

        db_widget = await self.widget_repository.get_by_id(widget_id)
        logger.debug(f"Preparing to zap widget ID {db_widget.id}")

        # start the async task and report the uuid
        result = widget_zap_task(
            WidgetZapParams(
                request_id=REQUEST_ID_CONTEXTVAR.get() or "UNKNOWN",
                widget_id=widget_id,
                duration=payload.duration,
            )
        )
        task_uuid = "PENDING"
        # if hasattr(result, "task"):
        task = getattr(result, "task")
        task_uuid = getattr(task, "id")

        task_md = {
            "uuid": task_uuid,
            "id": widget_id,
            "state": "PENDING",
            "duration": payload.duration,
            "runtime": 0,
        }
        store_task_metadata(huey_app, task_uuid, task_md)

        return WidgetZapTask.model_validate(task_md)

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

        Returns:
            WidgetZapTask: The retrieved widget.

        Raises:
            ResourceNotFoundError: Raised if the task UUID cannot be found.
        """
        await self._is_authz(self.acls, "read")

        db_widget = await self.widget_repository.get_by_id(widget_id)
        logger.debug(f"Fetching zap status for widget ID {db_widget.id}")

        # NOTE: missing result might mean the task is still running
        task_result = fetch_task_result(huey_app, task_uuid)
        if task_result:
            return WidgetZapTask.model_validate(task_result)

        # no result and no running metadata is a problem
        task_md = fetch_task_metadata(huey_app, task_uuid)
        if not task_result and not task_md:
            logger.debug(f"Task metadata not found for {task_uuid}")
            raise ResourceNotFoundError(task_uuid, "Task")

        return WidgetZapTask.model_validate(task_md)
