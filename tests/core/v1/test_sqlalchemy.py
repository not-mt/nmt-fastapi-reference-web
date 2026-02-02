# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for core SQLAlchemy functions."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.v1.settings import AppSettings, SqlAlchemySettings
from app.core.v1.sqlalchemy import with_huey_db_session


def test_with_ssl_mode_default_context():
    """
    Test creating an async_engine with ssl_mode="default"
    """
    test_url = "mysql+aiomysql://user:pass@host:3306"
    test_app_settings = AppSettings(
        sqlalchemy=SqlAlchemySettings(url=test_url, ssl_mode="default")
    )

    with patch(
        "app.core.v1.settings.get_app_settings",
        return_value=test_app_settings,
    ):
        # NOTE: reload module to re-execute initialization
        import importlib
        import ssl

        import app.core.v1.sqlalchemy as sqlalchemy_module

        importlib.reload(sqlalchemy_module)

        assert isinstance(sqlalchemy_module.ssl_context, ssl.SSLContext)


@pytest.mark.asyncio
async def test_with_huey_db_session_injects_db_session():
    """
    Test that with_huey_db_session injects a db_session and calls the wrapped function.
    """
    called_args = {}

    @with_huey_db_session
    async def dummy_function(x, y, db_session=None):
        called_args["x"] = x
        called_args["y"] = y
        called_args["db_session"] = db_session
        return "success"

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None
    # Ensure commit, rollback, and close are all AsyncMock too
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()

    with patch("app.core.v1.sqlalchemy.huey_session", return_value=mock_session):
        result = await dummy_function(1, 2)

    assert result == "success"
    assert called_args["x"] == 1
    assert called_args["y"] == 2
    assert called_args["db_session"] == mock_session
    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_not_called()
    mock_session.close.assert_awaited_once()
