# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for repository layer."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.v1.exceptions import ResourceNotFoundError
from app.layers.repository.v1.widgets import WidgetRepository
from app.schemas.dto.v1.widgets import WidgetCreate
from app.schemas.orm.v1.widgets import Widget


@pytest.fixture
def mock_async_session() -> AsyncMock:
    """
    Fixture to provide a mock AsyncSession.
    """
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_widget_create() -> WidgetCreate:
    """
    Fixture to provide a test WidgetCreate instance.
    """
    return WidgetCreate(name="Test Widget", height="10cm", mass="5kg", force=20)


@pytest.fixture
def mock_db_widget():
    """
    Fixture to create a mock Widget database object.
    """
    return Widget(id=1, name="Test Widget", height="10cm", mass="5kg", force=20)


@pytest.mark.asyncio
async def test_widget_create(
    mock_async_session: AsyncMock,
    mock_widget_create: WidgetCreate,
):
    """Test creating a widget in the repository."""

    repository = WidgetRepository(mock_async_session)
    mock_async_session.add.return_value = None
    mock_async_session.commit.return_value = None
    mock_async_session.refresh.return_value = None

    # NOTE: simulate assigning an 'id' to the object, without actually needing an
    #   underlying DB to do this for us, because this is a unit test
    mock_async_session.add.side_effect = lambda db_widget: setattr(db_widget, "id", 1)
    result = await repository.widget_create(mock_widget_create)

    mock_async_session.add.assert_called_once()
    mock_async_session.commit.assert_called_once()
    mock_async_session.refresh.assert_called_once()

    assert isinstance(result, Widget)
    assert result.name == mock_widget_create.name


@pytest.mark.asyncio
async def test_widget_get_by_id_found(
    mock_async_session: AsyncMock,
    mock_db_widget: Widget,
):
    """Test retrieving a widget by ID when it exists."""

    repository = WidgetRepository(mock_async_session)
    mock_async_session.get.return_value = mock_db_widget

    result = await repository.get_by_id(mock_db_widget.id)

    mock_async_session.get.assert_called_once_with(Widget, mock_db_widget.id)
    assert result == mock_db_widget


@pytest.mark.asyncio
async def test_widget_get_by_id_not_found(mock_async_session: AsyncMock):
    """Test retrieving a widget by ID when it does not exist."""

    repository = WidgetRepository(mock_async_session)
    mock_async_session.get.return_value = None

    with pytest.raises(ResourceNotFoundError):
        await repository.get_by_id(123)


@pytest.mark.asyncio
async def test_update_force_success(
    mock_async_session: AsyncMock,
    mock_db_widget: Widget,
):
    """Test successfully updating the force value of a widget."""

    repository = WidgetRepository(mock_async_session)
    mock_async_session.get.return_value = mock_db_widget
    mock_async_session.commit.return_value = None
    mock_async_session.refresh.return_value = None

    new_force = 42
    result = await repository.update_force(mock_db_widget.id, new_force)

    assert result is mock_db_widget
    assert result.force == new_force


@pytest.mark.asyncio
async def test_update_force_widget_not_found(mock_async_session: AsyncMock):
    """Test update_force raises ResourceNotFoundError when widget does not exist."""

    repository = WidgetRepository(mock_async_session)
    mock_async_session.get.return_value = None

    with pytest.raises(ResourceNotFoundError, match="Widget with ID 1 not found"):
        await repository.update_force(1, 123)
