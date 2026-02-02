# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Tests for gadget tasks."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from huey.api import Task as HueyTask
from pymongo import AsyncMongoClient

from app.schemas.dto.v1.gadgets import GadgetRead, GadgetZapTask
from app.tasks.v1.gadgets import (
    GadgetZapParams,
    _async_logic_gadget_zap,
    _async_mongo_gadget_zap,
    gadget_zap_task,
)


@pytest.fixture
def mock_gadget():
    """
    Fixture to return a mock Gadget DTO.
    """
    return GadgetRead(id="123", name="Mock Gadget", force=42)


@pytest.fixture
def mock_task():
    """
    Fixture to return a mock async task.
    """
    task = MagicMock(spec=HueyTask)
    task.id = "abc-123"
    return task


@pytest.fixture
def mock_mongo_client():
    """
    Fixture to return a mocked AsyncMongoClient.
    """
    mongo_client = MagicMock(spec=AsyncMongoClient)
    patcher = pytest.MonkeyPatch()
    # patcher.setattr("app.tasks.v1.gadgets.GadgetRepository", lambda _: repo_mock)
    yield mongo_client
    patcher.undo()
    return mongo_client


@pytest.mark.asyncio
async def test_async_logic_gadget_zap_success(monkeypatch, mock_task):
    """
    Test a successful zap of a gadget, isolated from async DB/huey wrappers.
    """
    mock_task = MagicMock()
    mock_task.id = "mock-task-id"
    params = GadgetZapParams(request_id="abc-123", gadget_id="gadget-42", duration=1)

    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = GadgetRead(id="gadget-42", name="test", force=5)
    mock_repo.update_force.return_value = None

    monkeypatch.setattr("app.tasks.v1.gadgets.GadgetRepository", lambda _: mock_repo)
    monkeypatch.setattr(
        "app.tasks.v1.gadgets.fetch_task_metadata",
        lambda _, __: GadgetZapTask(
            uuid="mock-task-id", id="gadget-42", state="PENDING", duration=1, runtime=0
        ),
    )
    monkeypatch.setattr("app.tasks.v1.gadgets.store_task_metadata", lambda *_: None)

    result = await _async_logic_gadget_zap(params, mock_task, mongo_client=MagicMock())

    assert isinstance(result, GadgetZapTask)
    assert result.state == "SUCCESS"
    assert result.runtime == 1


@pytest.mark.asyncio
async def test_async_mongo_gadget_zap_success(
    monkeypatch, mock_task, mock_mongo_client
):
    """
    Test a successful zap of a gadget, isolating the async Mongo wrapper.
    """
    expected = GadgetZapTask(
        uuid="abc-123", state="SUCCESS", id="123", duration=1, runtime=1
    )
    monkeypatch.setattr(
        "app.core.v1.mongo.AsyncMongoClient",
        lambda *args, **kwargs: mock_mongo_client,
    )
    monkeypatch.setattr(
        "app.tasks.v1.gadgets._async_logic_gadget_zap",
        AsyncMock(return_value=expected),
    )

    params = GadgetZapParams(request_id="req-1", gadget_id="123", duration=1)
    result = await _async_mongo_gadget_zap(
        params=params, task=mock_task, mongo_client=mock_mongo_client
    )

    assert result == expected


def test_gadget_zap_task_wrapper(monkeypatch):
    """
    Test a successful zap of a gadget, isolating the sync Huey task wrapper.
    """
    expected_result = GadgetZapTask(
        uuid="abc-123",
        state="SUCCESS",
        id="123",
        duration=0,
        runtime=0,
    )

    monkeypatch.setattr(
        "app.tasks.v1.gadgets._async_mongo_gadget_zap",
        lambda params, task: expected_result,
    )
    monkeypatch.setattr("app.tasks.v1.gadgets.asyncio.run", lambda coro: coro)

    params = GadgetZapParams(request_id="req-1", gadget_id="123", duration=0)
    task = MagicMock()
    result = gadget_zap_task.func(params=params, task=task)

    assert isinstance(result, GadgetZapTask)
    assert result == expected_result
