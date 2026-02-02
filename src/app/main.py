# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Main FastAPI application setup with routers and exception handlers."""

import logging
import logging.config
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import toml  # NOTE: support backwards compatibility <= Python 3.11
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from nmtfast.auth.v1.exceptions import AuthorizationError
from nmtfast.errors.v1.exceptions import UpstreamApiException
from nmtfast.logging.v1.config import create_logging_config
from nmtfast.middleware.v1.request_duration import RequestDurationMiddleware
from nmtfast.middleware.v1.request_id import RequestIDMiddleware

from app.core.v1.discovery import create_api_clients
from app.core.v1.health import set_app_not_ready, set_app_ready
from app.core.v1.kafka import create_kafka_consumers, create_kafka_producer
from app.core.v1.settings import AppSettings, get_app_settings
from app.core.v1.sqlalchemy import Base, async_engine
from app.errors.v1.exception_handlers import (
    authorization_error_handler,
    generic_not_found_error_handler,
    index_out_of_range_error_handler,
    resource_not_found_error_handler,
    server_error_handler,
    upstream_api_exception_handler,
)
from app.errors.v1.exceptions import ResourceNotFoundError
from app.layers.router.v1.gadgets import gadgets_router
from app.layers.router.v1.health import health_router
from app.layers.router.v1.upstream import widgets_api_router
from app.layers.router.v1.widgets import widgets_router

# load project metadata from pyproject.toml
with open("pyproject.toml", "rb") as f_reader:
    PROJECT_DATA = toml.loads(f_reader.read().decode("utf-8"))
    AUTHORS = "\n".join(
        f"- {x['name']} <{x['email']}>" for x in PROJECT_DATA["project"]["authors"]
    )

MD_DESCRIPTION = f"""
## Project Home

See complete project details at
[GitHub](https://github.com/not-mt/nmt-fastapi-reference).

## Features

- **RBAC with OAuth 2.0 & API Keys**: Secure endpoints with role- and resource-based
        access control.
- **Async RDBMS, MongoDB, Redis & Kafka**: Uses SQLAlchemy, Motor, aioredis, and
        aiokafka for non-blocking I/O.
- **Fully Asynchronous API**: Built on FastAPI with end-to-end async support.
- **Structured Logging**: Per-module control, request IDs, and customizable formatting.
- **Composable Config**: Merge settings from multiple files; isolate secrets as needed.

More details are available in the
[README.md](https://github.com/not-mt/nmt-fastapi-reference?tab=readme-ov-file) file.

## Authors
{AUTHORS}
"""


def custom_openapi(app: FastAPI):
    """
    Returns a closure that generates and caches the custom OpenAPI schema for the app.
    """

    def _openapi() -> dict:
        """
        Inner function to generate and cache the OpenAPI schema.
        """
        if app.openapi_schema:
            return app.openapi_schema

        project_version = PROJECT_DATA["project"].get("version", "0.1.0")
        project_description = PROJECT_DATA["project"].get(
            "description",
            "Missing pyproject.toml description",
        )

        openapi_schema = get_openapi(
            title="nmt-fastapi-reference",
            version=project_version,
            summary=project_description,
            description=MD_DESCRIPTION,
            routes=app.routes,
        )
        openapi_schema["info"]["x-logo"] = {
            "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
        }
        # NOTE: set servers manually when using custom OpenAPI schema
        openapi_schema["servers"] = [{"url": app.root_path or "/"}]

        app.openapi_schema = openapi_schema

        return app.openapi_schema

    return _openapi


def configure_logging(settings: AppSettings) -> None:
    """
    Configures the logging system based on the given settings.
    """
    logging_config: dict = create_logging_config(settings.logging)
    logging.config.dictConfig(logging_config)
    for logger_name, logger in settings.logging.loggers.items():
        log_level: int = getattr(logging, logger["level"].upper())
        logging.getLogger(logger_name).setLevel(log_level)


def register_routers() -> None:
    """
    Registers all API routers.
    """
    app.include_router(health_router)
    app.include_router(widgets_router)
    app.include_router(widgets_api_router)
    app.include_router(gadgets_router)


def register_exception_handlers() -> None:
    """
    Registers exception handlers for custom and built-in errors.
    """
    app.add_exception_handler(
        status.HTTP_404_NOT_FOUND,
        generic_not_found_error_handler,
    )
    app.add_exception_handler(
        ResourceNotFoundError,
        resource_not_found_error_handler,
    )
    app.add_exception_handler(
        IndexError,
        index_out_of_range_error_handler,
    )
    app.add_exception_handler(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        server_error_handler,
    )
    app.add_exception_handler(
        UpstreamApiException,
        upstream_api_exception_handler,
    )
    app.add_exception_handler(
        AuthorizationError,
        authorization_error_handler,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Handles application startup and shutdown events.

    This function is used to define actions that should be taken when the FastAPI
    application starts up and shuts down. It's especially useful for tasks like
    initializing resources (database connections) or cleaning up resources (closing
    connections).
    """
    logger: logging.Logger = logging.getLogger(__name__)
    logger.info("Lifespan started")

    logger.info("Initializing API Clients (if any)...")
    await create_api_clients()

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema created (only if necessary)")

    logger.info("Starting Kafka consumers/producer (if any)...")
    consumer_tasks = await create_kafka_consumers()
    kafka_producer = await create_kafka_producer()

    # NOTE: /health/readiness checks will pass after this
    set_app_ready()
    yield

    # NOTE: context manager handles graceful shutdown correctly--a signal
    #   handler for SIGTERM is not needed
    set_app_not_ready()

    logger.info("Shutting down Kafka consumers/producer (if any)...")
    if kafka_producer:
        await kafka_producer.stop()
    for task in consumer_tasks:
        task.cancel()

    logger.info("Lifespan ended")


# NOTE: ROOT_PATH is the equivalent of "SCRIPT_NAME" in WSGI, and specifies
#   a prefix that should be removed from  from route evaluation
root_path = os.getenv("ROOT_PATH", "")
print(f"Starting app with root_path='{root_path}'")

# Initialize FastAPI application and middleware
# NOTE: duration middleware must be first to log req IDs correctly
settings: AppSettings = get_app_settings()
app: FastAPI = FastAPI(
    title="nmt-fastapi-reference",
    lifespan=lifespan,
    root_path=root_path,
)
app.add_middleware(
    RequestDurationMiddleware, remote_headers=settings.logging.client_host_headers
)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# load custom OpenAPI schema for description, logo, etc
object.__setattr__(app, "openapi", custom_openapi(app))

# configure logging immediately after app creation
configure_logging(settings)

# finalize application setup
register_routers()
register_exception_handlers()
