# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""pytest fixtures for unit / integration tests."""

from unittest.mock import AsyncMock

import argon2
import pytest
from nmtfast.settings.v1.schemas import (
    IncomingAuthApiKey,
    IncomingAuthSettings,
    SectionACL,
)
from pymongo.asynchronous.database import AsyncDatabase as AsyncMongoDatabase

from app.core.v1.settings import (
    AppSettings,
    AuthSettings,
    KafkaSettings,
    LoggingSettings,
)

ph = argon2.PasswordHasher()


@pytest.fixture
def mock_mongo_db() -> AsyncMock:
    """
    Fixture to provide a mock AsyncMongoDatabase.
    """
    return AsyncMock(spec=AsyncMongoDatabase)


@pytest.fixture
def mock_api_key() -> str:
    """
    Fixture to return a predictable phrase that can be used to test hashing.
    """
    return "pytestapikey2"


@pytest.fixture(scope="function")
def mock_settings(mock_api_key: str) -> AppSettings:
    """
    Fixture to provide a generic AppSettings instance.
    """
    app_settings = AppSettings(
        auth=AuthSettings(
            swagger_token_url="http://localhost/token",
            id_providers={},
            incoming=IncomingAuthSettings(
                clients={},
                api_keys={
                    "key1": IncomingAuthApiKey(
                        contact="some.user@domain.tld",
                        memo="pytest fixture",
                        hash=ph.hash(mock_api_key),
                        algo="argon2",
                        acls=[SectionACL(section_regex=".*", permissions=["*"])],
                    )
                },
            ),
        ),
        kafka=KafkaSettings(
            enabled=True,
        ),
        logging=LoggingSettings(
            level="DEBUG",
            loggers={
                "test_logger_1": {"level": "DEBUG"},
                "test_logger_2": {"level": "WARNING"},
            },
        ),
    )
    return app_settings


@pytest.fixture
def mock_allow_acls() -> list[SectionACL]:
    """
    Fixture to provide a permissive set of ACLs.
    """
    acls = [
        SectionACL(section_regex=".*", permissions=["*"]),
    ]
    return acls


@pytest.fixture
def mock_deny_acls() -> list[SectionACL]:
    """
    Fixture to provide a restrictive set of ACLs.
    """
    acls = [
        SectionACL(section_regex=".*", permissions=[]),
    ]
    return acls
