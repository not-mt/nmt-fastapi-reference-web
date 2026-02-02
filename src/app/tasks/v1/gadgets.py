# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License.

"""Async tasks for gadget resources."""

import asyncio
import logging

from huey.api import Task
from nmtfast.middleware.v1.request_id import REQUEST_ID_CONTEXTVAR
from nmtfast.tasks.v1.huey import fetch_task_metadata, store_task_metadata
from pydantic import BaseModel
from pymongo.asynchronous.database import AsyncDatabase as AsyncMongoDatabase

from app.core.v1.mongo import with_huey_mongo_session
from app.core.v1.tasks import huey_app
from app.layers.repository.v1.gadgets import GadgetRepository
from app.schemas.dto.v1.gadgets import GadgetRead, GadgetZapTask

logger = logging.getLogger(__name__)


class GadgetZapParams(BaseModel):
    """Consolidated parameters for gadget_zap_task."""

    request_id: str
    gadget_id: str
    duration: int


async def _async_logic_gadget_zap(
    params: GadgetZapParams,
    task: Task,
    mongo_client: AsyncMongoDatabase,
) -> GadgetZapTask:
    """
    Core logic for gadget_zap_task.

    Args:
        params: Validated task parameters.
        task: Huey task object.
        mongo_client: Async MongoDB client.

    Returns:
        GadgetZapTask: Final task state after completion.
    """
    task_uuid = task.id
    REQUEST_ID_CONTEXTVAR.set(params.request_id)
    gadget_repo = GadgetRepository(mongo_client)

    db_gadget: GadgetRead = await gadget_repo.get_by_id(params.gadget_id)
    logger.debug(f"{task_uuid}: db_gadget: {db_gadget}")

    task_md = GadgetZapTask.model_validate(fetch_task_metadata(huey_app, task_uuid))
    task_md.state = "RUNNING"
    store_task_metadata(huey_app, task_uuid, task_md.model_dump())

    for tick in range(1, params.duration + 1):
        logger.debug(f"{task_uuid}: Progress {tick}/{params.duration}")
        task_md.runtime = tick
        store_task_metadata(huey_app, task_uuid, task_md.model_dump())
        await asyncio.sleep(1)

    current_force = db_gadget.force or 0
    await gadget_repo.update_force(params.gadget_id, current_force + 1)

    task_md.state = "SUCCESS"
    store_task_metadata(huey_app, task_uuid, task_md.model_dump())

    return task_md


@with_huey_mongo_session
async def _async_mongo_gadget_zap(
    params: GadgetZapParams,
    task: Task,
    mongo_client: AsyncMongoDatabase,
) -> GadgetZapTask:
    """
    Async DB wrapper for gadget_zap_task.

    Args:
        params: Validated task parameters.
        task: Huey task object.
        mongo_client: Async MongoDB client.

    Returns:
        GadgetZapTask: Task execution result.
    """
    return await _async_logic_gadget_zap(params, task, mongo_client)


@huey_app.task(retries=3, retry_delay=5, context=True)
def gadget_zap_task(params: GadgetZapParams, task: Task) -> GadgetZapTask:
    """
    Huey task wrapper for gadget_zap_task.

    Args:
        params: Validated task parameters (injected).
        task: Huey task object (injected).

    Returns:
        GadgetZapTask: Task execution result.
    """
    return asyncio.run(_async_mongo_gadget_zap(params, task))
