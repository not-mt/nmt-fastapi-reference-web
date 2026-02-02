# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Core functions for setting app readiness."""

import logging

logger = logging.getLogger(__name__)
is_ready: bool = False  # Application readiness flag, controlled by lifespan


def set_app_ready() -> None:
    """
    Mark the application as ready to receive requests.

    Sets the global readiness flag to True and logs the change.
    """
    global is_ready
    is_ready = True
    logger.info("App is ready to receive requests.")


def set_app_not_ready() -> None:
    """
    Mark the application as not ready to receive requests.

    Sets the global readiness flag to False and logs the change.
    """
    global is_ready
    is_ready = False
    logger.warning("App is NOT ready to receive requests.")


def check_app_readiness() -> bool:
    """
    Return the current application readiness state.

    Returns:
        bool: True if the app is ready; False otherwise.
    """
    return is_ready
