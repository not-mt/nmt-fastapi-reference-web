# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Application settings and defaults, defined with pydantic-settings."""

import logging
from typing import Literal, Optional

from nmtfast.settings.v1.config_files import get_config_files, load_config
from nmtfast.settings.v1.schemas import (
    AuthSettings,
    CacheSettings,
    IncomingAuthSettings,
    LoggingSettings,
    OutgoingAuthSettings,
    ServiceDiscoverySettings,
    TaskSettings,
)
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class SqlAlchemySettings(BaseModel):
    """SQLAlchemy database settings model."""

    url: str = "sqlite+aiosqlite:///./development.sqlite"
    ssl_mode: Literal["none", "default"] = "none"
    echo: bool = False
    connect_args: dict = {}
    echo_pool: bool = False
    max_overflow: int = 10
    pool_pre_ping: bool = True
    pool_size: int = 4
    pool_timeout: int = 30
    pool_recycle: int = 300


class MongoSettings(BaseModel):
    """MongoDB database settings model."""

    url: str = (
        "mongodb+srv://FIXME_username:FIXME_PASSWORD"
        "@cluster0.FIXME.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    )
    db: str = "nmt-fastapi-reference"


class CustomDiscoverySettings(ServiceDiscoverySettings):
    """
    Application-specific configuration for service discovery.

    This is a subclass of ServiceDiscoverySettings, and adds a "custom" field which
    serves as an example of how to integrate custom service/security settings while
    still using models from the nmtfast library.

    Attributes:
        custom: An example of custom fields that can be modeled by individual
            applications / microservices.
    """

    custom: dict[str, dict] = {}


class McpSettings(BaseModel):
    """
    Settings for MCP (Model Context Protocol) integration.

    Attributes:
        headers: Static headers to include in MCP requests.
        openapi_base_url: Base URL for OpenAPI specification.
        openapi_path: Path to the OpenAPI specification.
        mcp_mount_path: Mount path for the MCP interface.
        max_retries: Maximum number of retries for fetching the OpenAPI spec.
        stateless_http: Whether to use stateless or in-memory state/session tracking.
    """

    headers: dict[str, str] = {}
    openapi_base_url: str = "http://localhost:8000"
    openapi_path: str = "/openapi.json"
    mcp_mount_path: str = "/mcp"
    max_retries: int = 5
    stateless_http: bool = True


class KafkaSettings(BaseModel):
    """
    Kafka settings model.

    Configuration model for connecting to a Kafka cluster using aiokafka;
    supports optional security mechanisms including SASL and SSL.

    Attributes:
        enabled: Whether Kafka features are enabled in the application.

        bootstrap_servers: A list of Kafka broker addresses to connect to.
        group_id: The consumer group ID used to join a group for offset tracking.
        auto_offset_reset: Offset reset policy when no initial offset is present
            ("earliest", "latest", or "none").
        topics: A list of Kafka topics to subscribe to.

        security_protocol: Kafka security protocol to use. Options include
            "PLAINTEXT", "SSL", "SASL_PLAINTEXT", and "SASL_SSL".
        sasl_mechanism: SASL mechanism to use if a SASL-based protocol is selected.
            Supported mechanisms include "PLAIN", "SCRAM-SHA-256", and "SCRAM-SHA-512".
        sasl_plain_username: SASL authentication username, used with PLAIN or
            SCRAM mechanisms.
        sasl_plain_password: SASL authentication password, used with PLAIN or
            SCRAM mechanisms.

        ssl_cafile: Path to the CA certificate file for verifying the broker's
            certificate.
        ssl_certfile: Path to the client's SSL certificate file (optional, for mTLS).
        ssl_keyfile: Path to the client's SSL private key file (optional, for mTLS).
    """

    enabled: bool = False
    bootstrap_servers: list[str] = ["localhost:29092"]
    group_id: str = "nmt-fastapi-reference"
    auto_offset_reset: Literal["earliest", "latest", "none"] = "earliest"
    topics: list[str] = ["nmtfast-widgets"]
    security_protocol: Literal["PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL"] = (
        "PLAINTEXT"
    )
    sasl_mechanism: Optional[Literal["PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512"]] = None
    sasl_plain_username: Optional[str] = None
    sasl_plain_password: Optional[str] = None

    # TODO: add support for this later
    ssl_cafile: Optional[str] = None
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None


class AppSettings(BaseSettings):
    """Application settings model."""

    version: int = 1
    app_name: str = "nmt-fastapi-reference"
    sqlalchemy: SqlAlchemySettings = SqlAlchemySettings()
    mongo: MongoSettings = MongoSettings()
    auth: AuthSettings = AuthSettings(
        swagger_token_url="https://some.domain.tld/token",
        id_providers={},
        incoming=IncomingAuthSettings(
            clients={},
            api_keys={},
        ),
        outgoing=OutgoingAuthSettings(
            clients={},
            headers={},
        ),
    )
    discovery: CustomDiscoverySettings = CustomDiscoverySettings(
        mode="manual",
        services={},
        custom={},
    )
    mcp: McpSettings = McpSettings()
    kafka: KafkaSettings = KafkaSettings()
    logging: LoggingSettings = LoggingSettings()
    tasks: TaskSettings = TaskSettings(
        name="FIXME",
        backend="sqlite",
        url="redis://:FIXME_password@FIXME_host:6379/FIXME_db_number",
        sqlite_filename="./huey.sqlite",
    )
    cache: CacheSettings = CacheSettings(
        name="nmt-fastapi-reference",
        backend="huey",
        ttl=3600 * 4,
    )

    model_config = SettingsConfigDict(extra="ignore")


def get_app_settings() -> AppSettings:
    """
    Dependency function to provide settings.

    Returns:
        AppSettings: The application settings.
    """
    return _settings


_config_data: dict = load_config(get_config_files())
_settings: AppSettings = AppSettings(**_config_data)
