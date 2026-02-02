# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""pytest fixtures for unit / integration tests."""

import uuid
from unittest.mock import MagicMock

import pytest
from huey.api import Task


@pytest.fixture
def mock_task():
    """
    Fixture for a mock Huey Task object.
    """
    task = MagicMock(spec=Task)
    task.id = str(uuid.uuid4())

    return task
