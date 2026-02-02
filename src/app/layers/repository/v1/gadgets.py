# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Repository layer for Gadget resources."""

import logging
from typing import Any
from uuid import uuid4

from nmtfast.retry.v1.tenacity import tenacity_retry_log
from pymongo import ReturnDocument
from pymongo.asynchronous.collection import AsyncCollection as AsyncMongoCollection
from pymongo.asynchronous.database import AsyncDatabase as AsyncMongoDatabase
from tenacity import retry, stop_after_attempt, wait_fixed

from app.errors.v1.exceptions import ResourceNotFoundError
from app.schemas.dto.v1.gadgets import GadgetCreate, GadgetRead

logger = logging.getLogger(__name__)


class GadgetRepository:
    """
    Repository implementation for Gadget operations.

    Args:
        db: The asynchronous MongoDB database.
    """

    def __init__(self, db: AsyncMongoDatabase) -> None:
        self.db: AsyncMongoDatabase = db
        self.collection: AsyncMongoCollection = db["gadgets"]

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def gadget_create(self, gadget: GadgetCreate) -> GadgetRead:
        """
        Create a new gadget and persist it to the database.

        Args:
            gadget: The gadget data transfer object.

        Returns:
            GadgetRead: The newly created gadget instance.
        """
        new_gadget = gadget.model_dump()
        new_gadget["id"] = str(uuid4())

        await self.collection.insert_one(new_gadget)
        inserted_gadget = await self.collection.find_one({"id": new_gadget["id"]})
        logger.debug(f"Inserted gadget: {inserted_gadget}")

        return GadgetRead(**new_gadget)

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def get_by_id(self, gadget_id: str) -> GadgetRead:
        """
        Retrieve a gadget by its ID from the database.

        Args:
            gadget_id: The ID of the gadget to retrieve.

        Returns:
            GadgetRead: The retrieved gadget instance.

        Raises:
            ResourceNotFoundError: If the gadget is not found.
        """
        logger.debug(f"Fetching gadget by ID: {gadget_id}")
        db_gadget: dict[str, Any] | None = await self.collection.find_one(
            {"id": gadget_id}
        )

        if db_gadget is None:
            logger.warning(f"Gadget with ID {gadget_id} not found.")
            raise ResourceNotFoundError(gadget_id, "Gadget")

        logger.debug(f"Retrieved gadget: {db_gadget}")
        db_gadget.pop("_id", None)

        return GadgetRead(**db_gadget)

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def update_force(self, gadget_id: str, new_force: int) -> GadgetRead:
        """
        Update the force property of a gadget.

        Args:
            gadget_id: The ID of the gadget to retrieve.
            new_force: The new value for the force property.

        Returns:
            GadgetRead: The updated gadget.

        Raises:
            ResourceNotFoundError: If the gadget is not found.
        """
        logger.debug(f"Updating force for gadget ID {gadget_id} to {new_force}")
        db_gadget = await self.collection.find_one_and_update(
            {"id": gadget_id},
            {"$set": {"force": new_force}},
            return_document=ReturnDocument.AFTER,
        )

        if db_gadget is None:
            logger.warning(f"Gadget with ID {gadget_id} not found.")
            raise ResourceNotFoundError(gadget_id, "Gadget")

        logger.debug(f"Gadget ID {gadget_id} force updated to {new_force}")

        return GadgetRead(**db_gadget)
