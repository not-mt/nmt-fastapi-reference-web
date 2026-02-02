# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Core functions for configuring Kafka connections and processing messages."""

import asyncio
import json
import logging
from datetime import date, datetime
from decimal import Decimal
from json import JSONEncoder
from typing import Any, Optional

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from pydantic import BaseModel

from app.core.v1.settings import get_app_settings
from app.events.v1.kafka_demo import route_kafka_message

logger = logging.getLogger(__name__)
settings = get_app_settings()
kafka_producer: Optional[AIOKafkaProducer] = None


class EnhancedJSONEncoder(JSONEncoder):
    """
    JSON encoder that handles extended Python types.
    """

    def default(self, o: Any) -> Any:
        """
        Handle serialization of non-JSON-serializable types.

        Args:
            o: The object to serialize (named 'o' to match parent class signature).

        Returns:
            Any: The serialized representation of the object.

        Note:
            Maintains parent class behavior for all other types.
        """
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, BaseModel):
            return o.model_dump()
        return super().default(o)


def custom_serializer(value: Any) -> bytes:
    """
    Serialize any Python object to UTF-8 encoded JSON bytes.

    Args:
        value: The Python object to serialize.

    Returns:
        bytes: UTF-8 encoded JSON bytes representation of the value.
    """
    return json.dumps(value, cls=EnhancedJSONEncoder).encode("utf-8")


_sk = settings.kafka
_sasl_mechanism = _sk.sasl_mechanism if _sk.sasl_mechanism else ""
_sasl_plain_username = _sk.sasl_plain_username if _sk.sasl_plain_username else ""
_sasl_plain_password = _sk.sasl_plain_password if _sk.sasl_plain_password else ""

if _sk.enabled:
    kafka_producer = AIOKafkaProducer(
        bootstrap_servers=_sk.bootstrap_servers,  # type: ignore
        security_protocol=_sk.security_protocol,
        sasl_mechanism=_sasl_mechanism,
        sasl_plain_username=_sasl_plain_username,
        sasl_plain_password=_sasl_plain_password,
        key_serializer=lambda k: str(k).encode("utf-8"),
        value_serializer=custom_serializer,
    )


async def _start_demo_consumer() -> None:
    """
    Create and run the demo Kafka consumer.

    The consumer will subscribe to configured topics and process messages. In the event
    of an error, it will be reported and message processing will continue.
    """
    consumer = AIOKafkaConsumer(
        *_sk.topics,
        bootstrap_servers=_sk.bootstrap_servers,  # type: ignore
        security_protocol=_sk.security_protocol,
        sasl_mechanism=_sasl_mechanism,
        sasl_plain_username=_sasl_plain_username,
        sasl_plain_password=_sasl_plain_password,
        group_id=_sk.group_id,
        auto_offset_reset=_sk.auto_offset_reset,
        value_deserializer=lambda x: json.loads(x.decode("utf-8")),
    )
    try:
        await consumer.start()
        logger.info("Kafka demo consumer started")

        async for message in consumer:
            try:
                await route_kafka_message(message)
            except Exception as exc:
                logger.error(f"Error processing message: {exc}", exc_info=True)
    finally:
        logger.info("Stopping Kafka demo consumer...")
        await consumer.stop()
        logger.info("Stopped Kafka demo consumer")


async def create_kafka_consumers() -> list[asyncio.Task]:
    """
    Create async Kafka consumers based on application settings.

    Returns:
        list[asyncio.Task]: List of running consumer tasks, empty if Kafka is disabled.
    """
    task_list: list[asyncio.Task[None]] = []

    if _sk.enabled:
        task = asyncio.create_task(_start_demo_consumer())
        task_list.append(task)
        logger.debug("Kafka consumer(s) started")
    else:
        logger.info("Kafka is disabled, not starting consumers")

    return task_list


async def create_kafka_producer() -> Optional[AIOKafkaProducer]:
    """
    Initialize and start the singleton Kafka producer instance.

    Kafka may not be enabled and, for demonstration purposes, the service layer will
    check to see if _sk.enabled == True before attempting to produce a
    message.

    Returns:
        Optional[AIOKafkaProducer]: The producer instance if Kafka is enabled,
            None otherwise.

    Raises:
        RuntimeError: Raised if the Kafka is enabled and producer is uninitialized.
    """
    global kafka_producer

    if not _sk.enabled:
        logger.info("Kafka is disabled, not starting producer")
        return None

    if not isinstance(kafka_producer, AIOKafkaProducer):
        raise RuntimeError("Kafka producer not initialized")

    await kafka_producer.start()
    logger.debug("Kafka producer started")
    return kafka_producer
