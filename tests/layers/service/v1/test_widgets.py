# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for WebUIWidgetService."""

from unittest.mock import AsyncMock

import pytest
from nmtfast.htmx.v1.schemas import PaginationMeta
from nmtfast.repositories.widgets.v1.api import WidgetApiRepository
from nmtfast.repositories.widgets.v1.schemas import (
    WidgetCreate,
    WidgetRead,
    WidgetUpdate,
    WidgetZap,
    WidgetZapTask,
)

from app.layers.service.v1.widgets import WebUIWidgetService

MOCK_WIDGET = WidgetRead(id=1, name="Test", height="10", mass="5", force=20)
MOCK_PAGINATION = PaginationMeta(total=1, page=1, page_size=10)
MOCK_ZAP_TASK = WidgetZapTask(uuid="abc", state="RUNNING", id=1, duration=10, runtime=0)


@pytest.fixture
def mock_repo():
    """
    Fixture providing a mock WidgetApiRepository.
    """
    return AsyncMock(spec=WidgetApiRepository)


@pytest.fixture
def service(mock_repo):
    """
    Fixture providing a WebUIWidgetService with a mocked repository.
    """
    return WebUIWidgetService(mock_repo)


@pytest.mark.asyncio
async def test_list_widgets(service, mock_repo):
    """
    Test listing widgets delegates to repository.
    """
    mock_repo.get_all = AsyncMock(return_value=([MOCK_WIDGET], MOCK_PAGINATION))
    result = await service.list_widgets()
    assert result == ([MOCK_WIDGET], MOCK_PAGINATION)


@pytest.mark.asyncio
async def test_get_widget(service, mock_repo):
    """
    Test getting a widget by ID delegates to repository.
    """
    mock_repo.get_by_id = AsyncMock(return_value=MOCK_WIDGET)
    result = await service.get_widget(1)
    assert result == MOCK_WIDGET


@pytest.mark.asyncio
async def test_create_widget(service, mock_repo):
    """
    Test creating a widget delegates to repository.
    """
    data = WidgetCreate(name="New")
    mock_repo.widget_create = AsyncMock(return_value=MOCK_WIDGET)
    result = await service.create_widget(data)
    assert result == MOCK_WIDGET


@pytest.mark.asyncio
async def test_update_widget(service, mock_repo):
    """
    Test updating a widget delegates to repository.
    """
    data = WidgetUpdate(name="Updated")
    mock_repo.widget_update = AsyncMock(return_value=MOCK_WIDGET)
    result = await service.update_widget(1, data)
    assert result == MOCK_WIDGET


@pytest.mark.asyncio
async def test_delete_widget(service, mock_repo):
    """
    Test deleting a widget delegates to repository.
    """
    mock_repo.widget_delete = AsyncMock(return_value=None)
    await service.delete_widget(1)
    mock_repo.widget_delete.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_bulk_delete_widgets(service, mock_repo):
    """
    Test bulk deleting widgets delegates to repository.
    """
    mock_repo.widget_bulk_delete = AsyncMock(return_value=2)
    result = await service.bulk_delete_widgets([1, 2])
    assert result == 2


@pytest.mark.asyncio
async def test_bulk_update_widgets(service, mock_repo):
    """
    Test bulk updating widgets delegates to repository.
    """
    data = WidgetUpdate(name="Bulk")
    mock_repo.widget_bulk_update = AsyncMock(return_value=3)
    result = await service.bulk_update_widgets([1, 2, 3], data)
    assert result == 3


@pytest.mark.asyncio
async def test_zap_widget(service, mock_repo):
    """
    Test zapping a widget delegates to repository.
    """
    payload = WidgetZap(duration=10)
    mock_repo.widget_zap = AsyncMock(return_value=MOCK_ZAP_TASK)
    result = await service.zap_widget(1, payload)
    assert result == MOCK_ZAP_TASK


@pytest.mark.asyncio
async def test_get_zap_status(service, mock_repo):
    """
    Test getting zap status delegates to repository.
    """
    mock_repo.widget_zap_by_uuid = AsyncMock(return_value=MOCK_ZAP_TASK)
    result = await service.get_zap_status(1, "abc")
    assert result == MOCK_ZAP_TASK
