# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for core MongoDB functions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.v1.settings import AppSettings, MongoSettings

# NOTE: each test needs to import app.core.v1.kafka so that patching of objects
#   like kafka_producer can succeed


def test_mongo_clients_initialization_with_url():
    """
    Test clients are initialized when mongo.url is present.
    """
    test_app_settings = AppSettings(
        mongo=MongoSettings(url="mongodb://localhost:27017", db="test-db")
    )
    mock_async_client = MagicMock()
    mock_sync_client = MagicMock()
    mock_sync_client.address = ("localhost", 27017)

    with (
        patch(
            "app.core.v1.settings.get_app_settings",
            return_value=test_app_settings,
        ),
        patch(
            "pymongo.AsyncMongoClient",
            return_value=mock_async_client,
        ),
        patch(
            "pymongo.MongoClient",
            return_value=mock_sync_client,
        ),
    ):
        # NOTE: reload module to re-execute initialization code
        import importlib

        import app.core.v1.mongo as mongo_module

        importlib.reload(mongo_module)

        assert mongo_module.async_client is mock_async_client
        assert mongo_module.sync_client is mock_sync_client
        assert mongo_module.sync_client is not None
        assert mongo_module.sync_client.address == ("localhost", 27017)


def test_mongo_clients_not_initialized_without_url():
    """
    Test clients remain None when mongo.url is empty string.
    """
    test_app_settings = AppSettings(mongo=MongoSettings(url="", db="test-db"))

    with patch(
        "app.core.v1.settings.get_app_settings",
        return_value=test_app_settings,
    ):
        # NOTE: reload module to re-execute initialization code
        import importlib

        import app.core.v1.mongo as mongo_module

        importlib.reload(mongo_module)

        # verify clients were NOT initialized
        assert mongo_module.async_client is None
        assert mongo_module.sync_client is None


@pytest.mark.asyncio
async def test_with_huey_mongo_session_success():
    """
    Test that the decorator injects mongo_client and runs successfully.
    """
    from app.core.v1.mongo import with_huey_mongo_session

    called_args = {}

    @with_huey_mongo_session
    async def dummy_task(*args, **kwargs):
        called_args.update(kwargs)
        return "ok"

    async_client_mock = MagicMock()
    async_client_mock.__getitem__.return_value = AsyncMock()
    async_client_mock.close = AsyncMock()

    with patch("app.core.v1.mongo.AsyncMongoClient", return_value=async_client_mock):
        result = await dummy_task()

        assert result == "ok"
        assert "mongo_client" in called_args
        assert called_args["mongo_client"] == async_client_mock.__getitem__.return_value
        async_client_mock.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_with_huey_mongo_session_exception():
    """
    Test that the decorator logs and re-raises exceptions.
    """
    from app.core.v1.mongo import with_huey_mongo_session

    @with_huey_mongo_session
    async def failing_task(*args, **kwargs):
        raise ValueError("boom")

    async_client_mock = MagicMock()
    async_client_mock.__getitem__.return_value = AsyncMock()
    async_client_mock.close = AsyncMock()

    with patch("app.core.v1.mongo.AsyncMongoClient", return_value=async_client_mock):
        with pytest.raises(ValueError, match="boom"):
            await failing_task()

        async_client_mock.close.assert_awaited_once()
