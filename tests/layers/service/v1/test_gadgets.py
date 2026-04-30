# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for WebUIGadgetService."""

from unittest.mock import AsyncMock

import pytest
from nmtfast.htmx.v1.schemas import PaginationMeta
from nmtfast.repositories.gadgets.v1.api import GadgetApiRepository
from nmtfast.repositories.gadgets.v1.schemas import (
    GadgetCreate,
    GadgetRead,
    GadgetUpdate,
    GadgetZap,
    GadgetZapTask,
)

from app.layers.service.v1.gadgets import WebUIGadgetService

MOCK_GADGET = GadgetRead(id="g1", name="Test", height="10", mass="5", force=20)
MOCK_PAGINATION = PaginationMeta(total=1, page=1, page_size=10)
MOCK_ZAP_TASK = GadgetZapTask(
    uuid="abc", state="RUNNING", id="g1", duration=10, runtime=0
)


@pytest.fixture
def mock_repo():
    """
    Fixture providing a mock GadgetApiRepository.
    """
    return AsyncMock(spec=GadgetApiRepository)


@pytest.fixture
def service(mock_repo):
    """
    Fixture providing a WebUIGadgetService with a mocked repository.
    """
    return WebUIGadgetService(mock_repo)


@pytest.mark.asyncio
async def test_list_gadgets(service, mock_repo):
    """
    Test listing gadgets delegates to repository.
    """
    mock_repo.get_all = AsyncMock(return_value=([MOCK_GADGET], MOCK_PAGINATION))
    result = await service.list_gadgets()
    assert result == ([MOCK_GADGET], MOCK_PAGINATION)


@pytest.mark.asyncio
async def test_get_gadget(service, mock_repo):
    """
    Test getting a gadget by ID delegates to repository.
    """
    mock_repo.get_by_id = AsyncMock(return_value=MOCK_GADGET)
    result = await service.get_gadget("g1")
    assert result == MOCK_GADGET


@pytest.mark.asyncio
async def test_create_gadget(service, mock_repo):
    """
    Test creating a gadget delegates to repository.
    """
    data = GadgetCreate(name="New")
    mock_repo.gadget_create = AsyncMock(return_value=MOCK_GADGET)
    result = await service.create_gadget(data)
    assert result == MOCK_GADGET


@pytest.mark.asyncio
async def test_update_gadget(service, mock_repo):
    """
    Test updating a gadget delegates to repository.
    """
    data = GadgetUpdate(name="Updated")
    mock_repo.gadget_update = AsyncMock(return_value=MOCK_GADGET)
    result = await service.update_gadget("g1", data)
    assert result == MOCK_GADGET


@pytest.mark.asyncio
async def test_delete_gadget(service, mock_repo):
    """
    Test deleting a gadget delegates to repository.
    """
    mock_repo.gadget_delete = AsyncMock(return_value=None)
    await service.delete_gadget("g1")
    mock_repo.gadget_delete.assert_awaited_once_with("g1")


@pytest.mark.asyncio
async def test_bulk_delete_gadgets(service, mock_repo):
    """
    Test bulk deleting gadgets delegates to repository.
    """
    mock_repo.gadget_bulk_delete = AsyncMock(return_value=2)
    result = await service.bulk_delete_gadgets(["g1", "g2"])
    assert result == 2


@pytest.mark.asyncio
async def test_bulk_update_gadgets(service, mock_repo):
    """
    Test bulk updating gadgets delegates to repository.
    """
    data = GadgetUpdate(name="Bulk")
    mock_repo.gadget_bulk_update = AsyncMock(return_value=3)
    result = await service.bulk_update_gadgets(["g1", "g2", "g3"], data)
    assert result == 3


@pytest.mark.asyncio
async def test_zap_gadget(service, mock_repo):
    """
    Test zapping a gadget delegates to repository.
    """
    payload = GadgetZap(duration=10)
    mock_repo.gadget_zap = AsyncMock(return_value=MOCK_ZAP_TASK)
    result = await service.zap_gadget("g1", payload)
    assert result == MOCK_ZAP_TASK


@pytest.mark.asyncio
async def test_get_zap_status(service, mock_repo):
    """
    Test getting zap status delegates to repository.
    """
    mock_repo.gadget_zap_by_uuid = AsyncMock(return_value=MOCK_ZAP_TASK)
    result = await service.get_zap_status("g1", "abc")
    assert result == MOCK_ZAP_TASK
