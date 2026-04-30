# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""
Template dependency providing a shared Jinja2Templates instance.

Uses the library's configure_templates to set up a ChoiceLoader
that checks the application's own template directory first, then falls
back to the templates shipped inside the nmtfast package.
"""

from functools import lru_cache

from fastapi.templating import Jinja2Templates
from nmtfast.htmx.v1.helpers import configure_templates

APP_TEMPLATE_DIR: str = "src/app/templates"


@lru_cache(maxsize=1)
def get_templates() -> Jinja2Templates:
    """
    Return the application-wide Jinja2Templates instance (cached).

    Returns:
        Jinja2Templates: A configured template engine with ChoiceLoader.
    """
    return configure_templates(APP_TEMPLATE_DIR)
