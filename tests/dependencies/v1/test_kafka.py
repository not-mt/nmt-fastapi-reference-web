# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for Kafka dependency injection functions."""

from unittest.mock import Mock, patch

import pytest

from app.dependencies.v1.kafka import get_kafka_producer


@pytest.mark.asyncio
async def test_get_kafka_producer_returns_module_level_instance():
    """
    Ensure get_kafka_producer returns the module-level kafka_producer
    as seen from the dependencies module.
    """
    mock_producer = Mock()

    with patch("app.dependencies.v1.kafka.kafka_producer", mock_producer):
        result = await get_kafka_producer()
        assert result is mock_producer
