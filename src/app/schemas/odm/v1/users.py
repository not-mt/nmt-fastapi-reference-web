# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""ODM models for Users."""

from typing import Annotated, Optional

from beanie import Document, Indexed


class User(Document):
    """
    ODM model representing a user.
    """

    username: Annotated[str, Indexed(unique=True)]
    contact: str
    description: Optional[str]
