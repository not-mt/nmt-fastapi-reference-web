# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""ODM models for UserSettings."""

from typing import Annotated

from beanie import Document, Indexed, Link

from .users import User


class UserSetting(Document):
    """
    ODM model representing a user setting.
    """

    name: str
    value: Annotated[str, Indexed()]
    user: Link[User]
