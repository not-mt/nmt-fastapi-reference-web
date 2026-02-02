# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Discover Huey tasks and configure logging for workers."""

import importlib
import logging
import pathlib

from nmtfast.logging.v1.config import create_logging_config

from app.core.v1.settings import AppSettings, get_app_settings

# NOTE: we make huey_app available here so that it will be imported just
#   before our tasks are discovered and registered
from app.core.v1.tasks import huey_app  # noqa: F401

logger = logging.getLogger(__name__)


def configure_logging(settings: AppSettings) -> None:
    """
    Configures the logging system based on the given settings.
    """
    logging_config: dict = create_logging_config(settings.logging)
    logging.config.dictConfig(logging_config)
    for logger_name, logger in settings.logging.loggers.items():
        log_level: int = getattr(logging, logger["level"].upper())
        logging.getLogger(logger_name).setLevel(log_level)


def discover_tasks(package: str = "app.tasks") -> None:
    """
    Recursively import all task modules.

    This import all task modules in the given package so their @huey.task
    decorators are registered. This is how we are able to register our tasks
    and use implicit namespace packages, which allows us to avoid cluttering
    our code with __init__.py files.
    """
    spec = importlib.util.find_spec(package)
    if spec is None or spec.submodule_search_locations is None:
        raise ImportError(f"Could not find package {package}")

    base_path = pathlib.Path(next(iter(spec.submodule_search_locations)))

    for entry in base_path.rglob("*.py"):
        if entry.stem == "__init__":
            continue

        relative_path = entry.relative_to(base_path)
        module_name = (
            f"{package}.{relative_path.with_suffix('').as_posix().replace('/', '.')}"
        )

        importlib.import_module(module_name)
        logger.info(f"Loaded task module: {module_name}")


configure_logging(get_app_settings())
discover_tasks()
