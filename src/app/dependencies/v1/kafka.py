# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Dependencies related to Kafka."""

from aiokafka import AIOKafkaProducer
from fastapi import Depends

from app.core.v1.kafka import kafka_producer
from app.core.v1.settings import AppSettings, get_app_settings


async def get_kafka_producer(
    settings: AppSettings = Depends(get_app_settings),
) -> AIOKafkaProducer | None:
    """
    Provide dependency access to the Kafka producer.

    This returns the async producer that can be used to send messages to Kafka.

    Args:
        settings: The application settings.

    Returns:
        AIOKafkaProducer | None: An async Kafka producer, or None if Kafka support
            is not enabled.
    """
    return kafka_producer
