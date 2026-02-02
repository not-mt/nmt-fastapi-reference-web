# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for MongoDB dependency injection functions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymongo.asynchronous.database import AsyncDatabase as AsyncMongoDatabase

from app.dependencies.v1.mongo import get_mongo_db


@pytest.mark.asyncio
async def test_get_mongo_db_returns_correct_database():
    """
    Test that get_mongo_db returns a correct AsyncMongoDatabase instance.
    """

    mock_db_name = "test-db"
    mock_settings = MagicMock()
    mock_settings.mongo.db = mock_db_name
    mock_db = AsyncMock(spec=AsyncMongoDatabase)

    with patch("app.dependencies.v1.mongo.async_client", autospec=True) as mock_client:
        mock_client.__getitem__.return_value = mock_db
        db = await get_mongo_db(settings=mock_settings)

        mock_client.__getitem__.assert_called_once_with(mock_db_name)
        assert db is mock_db
        assert isinstance(db, AsyncMongoDatabase)
