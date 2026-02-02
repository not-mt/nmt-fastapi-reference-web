# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Business logic for processing Kafka messages."""

import logging

from aiokafka import ConsumerRecord

logger = logging.getLogger(__name__)


async def route_kafka_message(message: ConsumerRecord) -> None:
    """
    Demonstration on routing/processing a Kafka message.

    Args:
      message: The entire Kafka ConsumerRecord message (with topics, value, etc)
    """
    logger.info(f"Received Kafka message: {message}")
