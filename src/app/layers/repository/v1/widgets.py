# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Repository layer for Widget resources."""

import logging

from nmtfast.retry.v1.tenacity import tenacity_retry_log
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_fixed

from app.errors.v1.exceptions import ResourceNotFoundError
from app.schemas.dto.v1.widgets import WidgetCreate
from app.schemas.orm.v1.widgets import Widget

logger = logging.getLogger(__name__)


class WidgetRepository:
    """
    Repository implementation for Widget operations.

    Args:
        db: The asynchronous database session.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db: AsyncSession = db

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def widget_create(self, widget: WidgetCreate) -> Widget:
        """
        Create a new widget and persist it to the database.

        Args:
            widget: The widget data transfer object.

        Returns:
            Widget: The newly created widget instance.
        """
        db_widget = Widget(**widget.model_dump())
        self.db.add(db_widget)
        logger.debug(f"Adding widget: {widget.model_dump()}")

        await self.db.commit()
        await self.db.refresh(db_widget)

        return db_widget

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def get_by_id(self, widget_id: int) -> Widget:
        """
        Retrieve a widget by its ID from the database.

        Args:
            widget_id: The ID of the widget to retrieve.

        Returns:
            Widget: The retrieved widget instance.

        Raises:
            ResourceNotFoundError: If the widget is not found.
        """
        logger.debug(f"Fetching widget by ID: {widget_id}")
        db_widget = await self.db.get(Widget, widget_id)

        if db_widget is None:
            logger.warning(f"Widget with ID {widget_id} not found.")
            raise ResourceNotFoundError(widget_id, "Widget")
        logger.debug(f"Retrieved widget: {db_widget}")

        return db_widget

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def update_force(self, widget_id: int, new_force: int) -> Widget:
        """
        Update the force property of a widget.

        Args:
            widget_id: The ID of the widget to retrieve.
            new_force: The new value for the force property.

        Returns:
            Widget: The updated widget.

        Raises:
            ResourceNotFoundError: If the widget is not found.
        """
        logger.debug(f"Updating force for widget ID {widget_id} to {new_force}")
        db_widget = await self.db.get(Widget, widget_id)

        if db_widget is None:
            logger.warning(f"Widget with ID {widget_id} not found.")
            raise ResourceNotFoundError(widget_id, "Widget")
        logger.debug(f"Widget ID {widget_id} force updated to {new_force}")
        db_widget.force = new_force

        return db_widget
