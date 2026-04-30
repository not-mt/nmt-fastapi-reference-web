# -*- coding: utf-8 -*-
# Copyright (c) 2024. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Pydantic schema for user_settings."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserSettingBase(BaseModel):
    """Base schema for user_settings."""

    name: str = Field(..., description="Name of the user_setting.")
    value: str = Field(..., description="Value of the setting.")


class UserSettingCreate(UserSettingBase):
    """Schema for creating a new user_setting."""

    pass


class UserSettingRead(UserSettingBase):
    """Schema for reading a user_setting, including additional attributes."""

    id: str = Field(..., description="Database or unique ID of the user_setting.")
    user_id: Optional[str] = Field(
        default=None,
        description="ID of the user who owns this setting.",
    )
    model_config = ConfigDict(from_attributes=True)
