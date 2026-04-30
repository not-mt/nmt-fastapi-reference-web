# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for preferences dependency."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from nmtfast.auth.v1.sessions import SessionData

from app.dependencies.v1.preferences import DEFAULT_PAGE_SIZE, get_user_page_size
from app.schemas.dto.v1.user_settings import UserSettingRead


@pytest.mark.asyncio
async def test_get_user_page_size_no_session():
    """
    Test that default page size is returned when no session.
    """
    result = await get_user_page_size(session=None, db=MagicMock())
    assert result == DEFAULT_PAGE_SIZE


@pytest.mark.asyncio
async def test_get_user_page_size_with_setting():
    """
    Test that stored page size is returned when setting exists.
    """
    session = MagicMock(spec=SessionData)
    session.user_id = "u1"

    db = MagicMock()
    setting = UserSettingRead(id="s1", user_id="u1", name="page_size", value="25")

    with pytest.MonkeyPatch.context() as mp:
        mock_repo_cls = MagicMock()
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_by_user_and_name = AsyncMock(return_value=setting)
        mock_repo_cls.return_value = mock_repo_instance
        mp.setattr(
            "app.dependencies.v1.preferences.UserSettingRepository",
            mock_repo_cls,
        )
        result = await get_user_page_size(session=session, db=db)

    assert result == 25


@pytest.mark.asyncio
async def test_get_user_page_size_no_setting():
    """
    Test that default page size is returned when no setting exists.
    """
    session = MagicMock(spec=SessionData)
    session.user_id = "u1"

    db = MagicMock()

    with pytest.MonkeyPatch.context() as mp:
        mock_repo_cls = MagicMock()
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_by_user_and_name = AsyncMock(return_value=None)
        mock_repo_cls.return_value = mock_repo_instance
        mp.setattr(
            "app.dependencies.v1.preferences.UserSettingRepository",
            mock_repo_cls,
        )
        result = await get_user_page_size(session=session, db=db)

    assert result == DEFAULT_PAGE_SIZE


@pytest.mark.asyncio
async def test_get_user_page_size_exception():
    """
    Test that default page size is returned on exception.
    """
    session = MagicMock(spec=SessionData)
    session.user_id = "u1"

    db = MagicMock()

    with pytest.MonkeyPatch.context() as mp:
        mock_repo_cls = MagicMock()
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_by_user_and_name = AsyncMock(
            side_effect=Exception("db error")
        )
        mock_repo_cls.return_value = mock_repo_instance
        mp.setattr(
            "app.dependencies.v1.preferences.UserSettingRepository",
            mock_repo_cls,
        )
        result = await get_user_page_size(session=session, db=db)

    assert result == DEFAULT_PAGE_SIZE
