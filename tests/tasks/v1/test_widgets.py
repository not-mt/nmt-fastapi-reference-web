# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Tests for widget tasks."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.v1.exceptions import ResourceNotFoundError
from app.schemas.dto.v1.widgets import WidgetZapTask
from app.schemas.orm.v1.widgets import Widget
from app.tasks.v1.widgets import (
    WidgetZapParams,
    _async_db_widget_zap,
    _async_logic_widget_zap,
    widget_zap_task,
)


@pytest.fixture
def mock_widget():
    """
    Return a mock Widget object.
    """
    return Widget(id=1, name="Mock Widget", force=42)


@pytest.fixture
def mock_db_session(mock_widget):
    """
    Return a mocked AsyncSession with a get() method.
    """
    session = MagicMock(spec=AsyncSession)
    session.get = AsyncMock(return_value=mock_widget)
    return session


@pytest.fixture
def mock_task():
    """
    Return a mock Huey task with an ID.
    """
    task = MagicMock()
    task.id = "abc-123"
    return task


@pytest.mark.asyncio
async def test_async_logic_widget_zap_success(
    monkeypatch, mock_widget, mock_task, mock_db_session
):
    """
    Test successful widget zap logic.
    """

    monkeypatch.setattr(
        "app.tasks.v1.widgets.fetch_task_metadata",
        lambda huey_app, task_id: WidgetZapTask(
            uuid=task_id, state="PENDING", id=mock_widget.id, duration=1, runtime=0
        ),
    )
    monkeypatch.setattr(
        "app.tasks.v1.widgets.store_task_metadata", lambda huey_app, uuid, payload: None
    )

    params = WidgetZapParams(request_id="req-1", widget_id=mock_widget.id, duration=1)

    result = await _async_logic_widget_zap(
        params=params, task=mock_task, db_session=mock_db_session
    )

    assert isinstance(result, WidgetZapTask)
    assert result.id == mock_widget.id
    assert result.state == "SUCCESS"


@pytest.mark.asyncio
async def test_async_logic_widget_zap_not_found(monkeypatch, mock_task):
    """
    Test widget zap logic when widget is missing.
    """

    mock_session = MagicMock(spec=AsyncSession)
    mock_session.get = AsyncMock(return_value=None)

    params = WidgetZapParams(request_id="req-1", widget_id=9999, duration=0)

    with pytest.raises(ResourceNotFoundError, match="not found"):
        await _async_logic_widget_zap(
            params=params, task=mock_task, db_session=mock_session
        )


@pytest.mark.asyncio
async def test_async_db_widget_zap_success(monkeypatch, mock_task, mock_db_session):
    """
    Test successful execution of DB wrapper.
    """

    expected = WidgetZapTask(
        uuid="abc-123", state="SUCCESS", id=1, duration=1, runtime=1
    )

    monkeypatch.setattr(
        "app.tasks.v1.widgets._async_logic_widget_zap",
        AsyncMock(return_value=expected),
    )

    params = WidgetZapParams(request_id="req-1", widget_id=1, duration=1)
    result = await _async_db_widget_zap(
        params=params, task=mock_task, db_session=mock_db_session
    )

    assert result == expected


@pytest.mark.asyncio
async def test_async_db_widget_zap_missing_dependencies():
    """
    Test DB wrapper with missing task and session.
    """

    params = WidgetZapParams(request_id="req-1", widget_id=1, duration=1)

    with pytest.raises(ValueError, match="Missing required dependencies"):
        await _async_db_widget_zap(params=params, task=None, db_session=None)


def test_widget_zap_task_wrapper(monkeypatch):
    """
    Test the synchronous Huey task.
    """
    expected_result = WidgetZapTask(
        uuid="abc-123",
        state="SUCCESS",
        id=1,
        duration=0,
        runtime=0,
    )

    # patch the coroutine function to a normal function returning the result
    monkeypatch.setattr(
        "app.tasks.v1.widgets._async_db_widget_zap",
        lambda params, task: expected_result,
    )

    # also patch asyncio.run to return its input (which will be our expected result)
    monkeypatch.setattr(
        "app.tasks.v1.widgets.asyncio.run",
        lambda coro: coro,  # coro is actually the expected_result here
    )

    params = WidgetZapParams(request_id="req-1", widget_id=1, duration=0)
    task = MagicMock()
    result = widget_zap_task.func(params=params, task=task)

    assert isinstance(result, WidgetZapTask)
    assert result == expected_result
