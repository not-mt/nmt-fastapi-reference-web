# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Async tasks for widget resources."""

import asyncio
import logging
from typing import Optional

from huey.api import Task
from nmtfast.middleware.v1.request_id import REQUEST_ID_CONTEXTVAR
from nmtfast.tasks.v1.huey import fetch_task_metadata, store_task_metadata
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.v1.sqlalchemy import with_huey_db_session
from app.core.v1.tasks import huey_app
from app.layers.repository.v1.widgets import WidgetRepository
from app.schemas.dto.v1.widgets import WidgetZapTask
from app.schemas.orm.v1.widgets import Widget

logger = logging.getLogger(__name__)


class WidgetZapParams(BaseModel):
    """Consolidated parameters for widget_zap_task."""

    request_id: str
    widget_id: int
    duration: int


async def _async_logic_widget_zap(
    params: WidgetZapParams,
    task: Task,
    db_session: AsyncSession,
) -> WidgetZapTask:
    """
    Core logic for widget_zap_task.

    This function contains no decorators and is fully testable.

    Args:
        params: Validated parameters container.
        task: Huey task (injected earlier by wrapper).
        db_session: SQLAlchemy async session (injected earlier by wrapper).

    Returns:
        WidgetZapTask: Final state of the zap task.
    """
    task_uuid = task.id
    REQUEST_ID_CONTEXTVAR.set(params.request_id)
    widget_repo = WidgetRepository(db_session)

    db_widget: Widget = await widget_repo.get_by_id(params.widget_id)
    logger.debug(f"{task_uuid}: db_widget: {db_widget}")

    task_md = WidgetZapTask.model_validate(fetch_task_metadata(huey_app, task_uuid))
    task_md.state = "RUNNING"
    store_task_metadata(huey_app, task_uuid, task_md.model_dump())

    for tick in range(1, params.duration + 1):
        logger.debug(f"{task_uuid}: Progress {tick}/{params.duration}")
        task_md.runtime = tick
        store_task_metadata(huey_app, task_uuid, task_md.model_dump())
        await asyncio.sleep(1)

    await widget_repo.update_force(params.widget_id, db_widget.force + 1)
    # NOTE: commit will be handled by the session manager

    task_md.state = "SUCCESS"
    store_task_metadata(huey_app, task_uuid, task_md.model_dump())
    logger.info(f"{task_uuid}: Completed. New force: {db_widget.force}")

    return task_md


@with_huey_db_session
async def _async_db_widget_zap(
    params: WidgetZapParams,
    task: Task,
    db_session: Optional[AsyncSession] = None,  # injected by decorator
) -> WidgetZapTask:
    """
    Async wrapper that delegates to core logic with injected dependencies.

    Args:
        params: Validated parameters.
        task: Huey task (injected).
        db_session: SQLAlchemy session (injected).

    Returns:
        WidgetZapTask: Final state of the zap task.

    Raises:
        ValueError: If any required dependency is missing.
    """
    if not task or not db_session:
        raise ValueError("Missing required dependencies for task execution.")

    return await _async_logic_widget_zap(params, task, db_session)


@huey_app.task(retries=3, retry_delay=5, context=True)
def widget_zap_task(params: WidgetZapParams, task: Task) -> WidgetZapTask:
    """
    Huey task wrapper that calls async DB wrapper.

    Args:
        params: Validated task parameters (injected).
        task: Huey task object (injected).

    Returns:
        WidgetZapTask: Task execution result.
    """
    # NOTE: this function cannot be decorated with @with_huey_db_session because
    #   it must not be an async def, and @with_huey_db_session will only work
    #   with an async def
    return asyncio.run(_async_db_widget_zap(params, task))
