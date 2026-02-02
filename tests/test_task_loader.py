# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Test discovery of Huey tasks."""

import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.task_loader import discover_tasks


def test_discover_tasks_raises_import_error_when_spec_is_none():
    """
    Test discover_tasks() raises ImportError if importlib cannot find the package.
    """
    with patch("importlib.util.find_spec", return_value=None):
        with pytest.raises(ImportError, match="Could not find package"):
            discover_tasks("fake.package")


def test_discover_tasks_raises_import_error_when_submodule_locations_is_none():
    """
    Test discover_tasks() raises ImportError if submodule_search_locations is None.
    """
    mock_spec = types.SimpleNamespace(submodule_search_locations=None)
    with patch("importlib.util.find_spec", return_value=mock_spec):
        with pytest.raises(ImportError, match="Could not find package"):
            discover_tasks("another.fake.package")


def test_discover_tasks_skips_init():
    """
    Test discover_tasks() skips importing __init__.py during task module discovery.
    """
    mock_spec = types.SimpleNamespace(submodule_search_locations=["/fake/path"])

    init_file = MagicMock(spec=Path)
    init_file.stem = "__init__"
    init_file.suffix = ".py"
    init_file.relative_to.return_value = Path("__init__.py")
    init_file.with_suffix.return_value = Path("__init__")

    with (
        patch("importlib.util.find_spec", return_value=mock_spec),
        patch("pathlib.Path.rglob", return_value=[init_file]),
        patch("importlib.import_module") as mock_import,
    ):
        discover_tasks()

    mock_import.assert_not_called()  # __init__.py should be skipped
