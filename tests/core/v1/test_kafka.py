# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for core Kafka functions."""

import asyncio
import json
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiokafka import AIOKafkaProducer
from pydantic import BaseModel

from app.core.v1.settings import AppSettings, KafkaSettings

# NOTE: each test needs to import app.core.v1.kafka so that patching of objects
#   like kafka_producer can succeed


def test_enhanced_json_encoder():
    """
    Test EnhancedJSONEncoder handles extended types.
    """
    from app.core.v1.kafka import EnhancedJSONEncoder

    encoder = EnhancedJSONEncoder()

    # Test datetime
    now = datetime.now()
    assert encoder.default(now) == now.isoformat()

    # Test date
    today = date.today()
    assert encoder.default(today) == today.isoformat()

    # Test Decimal
    dec = Decimal("3.14")
    assert encoder.default(dec) == float(dec)

    # Test Pydantic model
    class TestModel(BaseModel):
        value: int

    model = TestModel(value=42)
    assert encoder.default(model) == model.model_dump()

    # Test fallback to parent class
    class Unhandled:
        def __str__(self):
            return "unhandled"

    unhandled = Unhandled()

    with pytest.raises(
        TypeError
    ):  # default() calls super().default(), which raises for unknown types
        encoder.default(unhandled)


def test_custom_serializer():
    """
    Test custom_serializer produces correct UTF-8 encoded JSON bytes.
    """
    from app.core.v1.kafka import custom_serializer

    test_data = {"date": date(2025, 1, 1), "decimal": Decimal("10.5"), "string": "test"}
    result = custom_serializer(test_data)

    assert isinstance(result, bytes)
    assert result == b'{"date": "2025-01-01", "decimal": 10.5, "string": "test"}'


@pytest.mark.asyncio
async def test_kafka_producer_initialization_with_auth():
    """
    Test producer is initialized when Kafka is enabled with auth.
    """
    mock_producer_instance = MagicMock()

    test_settings = AppSettings(
        kafka=KafkaSettings(
            enabled=True,
            bootstrap_servers=["localhost:9092"],
            group_id="test-group",
            security_protocol="SASL_PLAINTEXT",
            sasl_mechanism="PLAIN",
            sasl_plain_username="user",
            sasl_plain_password="pass",
        )
    )

    with (
        patch(
            "app.core.v1.settings.get_app_settings",
            return_value=test_settings,
        ),
        patch(
            "app.core.v1.kafka.AIOKafkaProducer",
            return_value=mock_producer_instance,
        ),
    ):
        # reload after patches to trigger producer creation with mocked settings
        import importlib

        import app.core.v1.kafka as kafka_module

        importlib.reload(kafka_module)

        # assert the global kafka_producer was initialized
        assert isinstance(kafka_module.kafka_producer, AIOKafkaProducer)
        assert kafka_module.kafka_producer.client._sasl_plain_username == "user"
        assert kafka_module.kafka_producer.client._sasl_plain_password == "pass"


def test_kafka_producer_not_initialized_when_disabled():
    """
    Test producer remains None when Kafka is disabled.
    """
    test_app_settings = MagicMock()
    test_app_settings.kafka = MagicMock(enabled=False)

    with patch("app.core.v1.kafka.settings", test_app_settings):
        import importlib

        import app.core.v1.kafka as kafka_module

        importlib.reload(kafka_module)

        assert kafka_module.kafka_producer is None


@pytest.mark.asyncio
async def test_create_kafka_producer_success():
    """
    Test create_kafka_producer starts and returns producer when enabled.
    """
    # patch settings and inject a mock producer before import
    mock_producer = AsyncMock(spec=AIOKafkaProducer)
    mock_producer.start = AsyncMock()

    test_settings = AppSettings(
        kafka=KafkaSettings(
            enabled=True,
            bootstrap_servers=["localhost:9092"],
            group_id="test-group",
            security_protocol="SASL_PLAINTEXT",
            sasl_mechanism="PLAIN",
            sasl_plain_username="user",
            sasl_plain_password="pass",
        )
    )

    with (
        patch("app.core.v1.settings.get_app_settings", return_value=test_settings),
        patch("app.core.v1.kafka.AIOKafkaProducer", return_value=mock_producer),
    ):
        # reload after patches to trigger producer creation with mocked settings
        import importlib

        import app.core.v1.kafka as kafka_module

        importlib.reload(kafka_module)

        # manually assign mock to the global so the function can use it
        kafka_module.kafka_producer = mock_producer
        result = await kafka_module.create_kafka_producer()

        assert result is mock_producer
        mock_producer.start.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_kafka_producer_disabled():
    """
    Test create_kafka_producer returns None when Kafka is disabled.
    """
    with patch("app.core.v1.kafka._sk", MagicMock(enabled=False)):
        from app.core.v1.kafka import create_kafka_producer

        result = await create_kafka_producer()
        assert result is None


@pytest.mark.asyncio
async def test_create_kafka_producer_uninitialized():
    """
    Test create_kafka_producer raises RuntimeError when uninitialized.
    """
    with (
        patch("app.core.v1.kafka._sk", MagicMock(enabled=True)),
        patch("app.core.v1.kafka.kafka_producer", None),
        pytest.raises(RuntimeError, match="Kafka producer not initialized"),
    ):
        from app.core.v1.kafka import create_kafka_producer

        await create_kafka_producer()


@pytest.mark.asyncio
async def test_start_demo_consumer_success():
    """
    Test _start_demo_consumer processes messages successfully.
    """
    mock_consumer = AsyncMock()
    mock_consumer.__aiter__.return_value = [MagicMock(value={"test": "message"})]

    with (
        patch("app.core.v1.kafka.AIOKafkaConsumer", return_value=mock_consumer),
        patch("app.core.v1.kafka.route_kafka_message", AsyncMock()),
        patch(
            "app.core.v1.kafka._sk",
            MagicMock(
                enabled=True,
                bootstrap_servers=["localhost:9092"],
                topics=["test_topic"],
                security_protocol="PLAINTEXT",
            ),
        ),
    ):
        from app.core.v1.kafka import _start_demo_consumer

        await _start_demo_consumer()
        mock_consumer.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_demo_consumer_exception(caplog):
    """
    Test that _start_demo_consumer logs exception when message processing fails.
    """
    from app.core.v1 import kafka as kafka_module

    mock_consumer = AsyncMock()
    mock_consumer.__aiter__.return_value = [
        MagicMock(
            value=json.dumps({"foo": "bar"}).encode("utf-8"),
        )
    ]
    mock_consumer.start = AsyncMock()
    mock_consumer.stop = AsyncMock()

    with (
        patch("app.core.v1.kafka.AIOKafkaConsumer", return_value=mock_consumer),
        patch("app.core.v1.kafka.route_kafka_message", side_effect=Exception("Boom!")),
    ):
        with caplog.at_level("ERROR"):
            await kafka_module._start_demo_consumer()

        assert "Error processing message: Boom!" in caplog.text

    mock_consumer.start.assert_awaited_once()
    mock_consumer.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_kafka_consumers_enabled():
    """
    Test create_kafka_consumers creates tasks when Kafka is enabled.
    """
    # NOTE: DO NOT AsyncMock tasks here! You will spend hours trying to figure out
    #   why you are getting random errors about an AsycMockMixin never being awaited!
    #
    # mock_task = AsyncMock(spec=asyncio.Task)  # <-- this will create problems!
    #
    # I had to use this to trace the problem down to scheduling MagicMock:
    #
    #       python -X tracemalloc=10 -m pytest -sS
    #
    # ...otherwise I would see errors like:
    #
    #   RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited
    #       def __init__(self, name, parent):
    #   Enable tracemalloc to get traceback where the object was allocated.
    #   See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings
    #   for more info.

    with (
        patch("app.core.v1.kafka._sk", MagicMock(enabled=True)),
        patch("app.core.v1.kafka._start_demo_consumer", AsyncMock()),
        # patch("asyncio.create_task", return_value=mock_task),
    ):
        from app.core.v1.kafka import create_kafka_consumers

        tasks = await create_kafka_consumers()
        await asyncio.gather(*tasks)
        assert len(tasks) == 1


@pytest.mark.asyncio
async def test_create_kafka_consumers_disabled():
    """
    Test create_kafka_consumers returns empty list when Kafka is disabled.
    """
    with patch("app.core.v1.kafka._sk", MagicMock(enabled=False)):
        from app.core.v1.kafka import create_kafka_consumers

        tasks = await create_kafka_consumers()
        assert tasks == []
