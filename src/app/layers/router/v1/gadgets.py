# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""This module defines API endpoints for managing gadgets."""

import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, status
from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.settings.v1.schemas import SectionACL
from pymongo.asynchronous.database import AsyncDatabase as AsyncMongoDatabase

from app.core.v1.settings import AppSettings
from app.dependencies.v1.auth import authenticate_headers, get_acls
from app.dependencies.v1.cache import get_cache
from app.dependencies.v1.mongo import get_mongo_db
from app.dependencies.v1.settings import get_settings
from app.layers.repository.v1.gadgets import GadgetRepository
from app.layers.service.v1.gadgets import GadgetService
from app.schemas.dto.v1.gadgets import (
    GadgetCreate,
    GadgetRead,
    GadgetZap,
    GadgetZapTask,
)

logger = logging.getLogger(__name__)
gadgets_router = APIRouter(
    prefix="/v1/gadgets",
    tags=["Gadget Operations (MongoDB)"],
    dependencies=[Depends(authenticate_headers)],
)


def get_gadget_service(
    db: AsyncMongoDatabase = Depends(get_mongo_db),
    acls: list[SectionACL] = Depends(get_acls),
    settings: AppSettings = Depends(get_settings),
    cache: AppCacheBase = Depends(get_cache),
) -> GadgetService:
    """
    Dependency function to provide a GadgetService instance.

    Args:
        db: The asynchronous MongoDB database.
        acls: List of ACLs associated with authenticated client/apikey.
        settings: The application's AppSettings object.
        cache: An implementation of AppCacheBase, for getting/setting cache data.

    Returns:
        GadgetService: An instance of the gadget service.
    """
    gadget_repository = GadgetRepository(db)

    return GadgetService(gadget_repository, acls, settings, cache)


@gadgets_router.post(
    path="",
    response_model=GadgetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a gadget",
    description="Create a gadget",  # Override the docstring in Swagger UI
)
async def gadget_create(
    gadget: Annotated[
        GadgetCreate,
        Body(
            openapi_examples={
                "normal": {
                    "summary": "Create a gadget",
                    "description": (
                        "A **normal** gadget that is created successfully."
                    ),
                    "value": {
                        "name": "gadget-123",
                        "height": "15cm",
                        "mass": "0.8kg",
                        "force": 1,
                    },
                },
            },
        ),
    ],
    gadget_service: GadgetService = Depends(get_gadget_service),
) -> GadgetRead:
    """
    Create a new gadget.

    Args:
        gadget: The gadget data provided in the request.
        gadget_service: The gadget service instance.

    Returns:
        GadgetRead: The created gadget data.
    """
    logger.info(f"Attempting to create a gadget: {gadget}")
    return await gadget_service.gadget_create(gadget)


@gadgets_router.get(
    "/{gadget_id}",
    response_model=GadgetRead,
    status_code=status.HTTP_200_OK,
    summary="View (read) a gadget",
    description="View (read) a gadget",  # Override the docstring in Swagger UI
)
async def gadget_get_by_id(
    gadget_id: Annotated[
        str,
        Path(description="The ID of the gadget to retrieve."),
    ],
    gadget_service: GadgetService = Depends(get_gadget_service),
) -> GadgetRead:
    """
    Retrieve a gadget by its ID.

    Args:
        gadget_id: The ID of the gadget to retrieve.
        gadget_service: The gadget service instance.

    Returns:
        GadgetRead: The retrieved gadget data.
    """
    logger.info(f"Attempting to find gadget {gadget_id}")
    return await gadget_service.gadget_get_by_id(gadget_id)


@gadgets_router.post(
    "/{gadget_id}/zap",
    response_model=GadgetZapTask,
    # TODO: add custom response which includes Location header!
    status_code=status.HTTP_202_ACCEPTED,
    summary="Zap a gadget",
    description="Zap a gadget",  # Override the docstring in Swagger UI
)
async def gadget_zap(
    gadget_id: Annotated[
        str,
        Path(description="The ID of the gadget to zap."),
    ],
    payload: Annotated[
        GadgetZap,
        Body(
            openapi_examples={
                "normal": {
                    "summary": "Zap a gadget",
                    "description": (
                        "A task is created to zap the gadget for `duration` seconds."
                    ),
                    "value": {
                        "duration": 10,
                    },
                },
            },
        ),
    ],
    gadget_service: GadgetService = Depends(get_gadget_service),
) -> GadgetZapTask:
    """
    Zaps an existing gadget.

    Args:
        gadget_id: The ID of the gadget to zap.
        payload: The gadget task parameters.
        gadget_service: The gadget service instance.

    Returns:
        GadgetZapTask: Information about the new task that was created.
    """
    logger.info(f"Attempting to zap gadget {gadget_id}: {payload}")
    return await gadget_service.gadget_zap(gadget_id, payload)


@gadgets_router.get(
    "/{gadget_id}/zap/{task_uuid}/status",
    response_model=GadgetZapTask,
    status_code=status.HTTP_200_OK,
    summary="View async task status",
    description="View async task status",  # Override the docstring in Swagger UI
)
async def gadget_zap_get_task(
    gadget_id: Annotated[
        str,
        Path(description="The ID of the gadget to retrieve."),
    ],
    task_uuid: Annotated[
        str,
        Path(description="The UUID of the async zap task."),
    ],
    gadget_service: GadgetService = Depends(get_gadget_service),
) -> GadgetZapTask:
    """
    Retrieve a zap gadget task by its UUID.

    Args:
        gadget_id: The ID of the gadget to retrieve.
        task_uuid: The UUID of the async task.
        gadget_service: The gadget service instance.

    Returns:
        GadgetZapTask: The retrieved gadget task data.
    """
    logger.info(f"Attempting to find zap status for task {task_uuid}")
    return await gadget_service.gadget_zap_by_uuid(gadget_id, task_uuid)
