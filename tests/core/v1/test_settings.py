# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for core settings functions."""

from app.core.v1 import settings
from app.core.v1.settings import (
    AppSettings,
    LoggingSettings,
    SqlAlchemySettings,
)


def test_sqlalchemy_settings():
    """Test SqlAlchemySettings model."""
    settings = SqlAlchemySettings(url="test_url")
    assert settings.url == "test_url"


def test_logging_settings():
    """Test LoggingSettings model."""
    settings = LoggingSettings(
        level="DEBUG",
        format="test_format",
        loggers={
            "test_logger": {"level": "INFO"},
        },
    )
    assert settings.level == "DEBUG"
    assert settings.format == "test_format"
    assert settings.loggers == {"test_logger": {"level": "INFO"}}


def test_app_settings():
    """Test AppSettings model."""
    settings = AppSettings(
        app_name="Test App",
        sqlalchemy=SqlAlchemySettings(url="test_db"),
        logging=LoggingSettings(level="WARNING"),
    )
    assert settings.app_name == "Test App"
    assert settings.sqlalchemy.url == "test_db"
    assert settings.logging.level == "WARNING"


def test_get_app_settings():
    """Test get_app_settings."""
    settings._settings = AppSettings(app_name="Test Get App Settings")
    assert settings.get_app_settings().app_name == "Test Get App Settings"
