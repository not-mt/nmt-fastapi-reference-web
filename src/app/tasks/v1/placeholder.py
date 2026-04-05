# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""
Placeholder task module.

This module exists so that discover_tasks() has at least one module to
import.  Replace or remove it once real tasks are defined.
"""

import logging

from app.core.v1.tasks import huey_app

logger = logging.getLogger(__name__)


@huey_app.task()
def placeholder_task() -> str:
    """
    A no-op task used as a placeholder.

    Returns:
        str: A confirmation string.
    """
    logger.info("placeholder_task executed")
    return "ok"
