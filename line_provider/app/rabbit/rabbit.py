import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import aio_pika
from app.config import settings

logger = logging.getLogger(__name__)


class RabbitMQSessionManager:
    def __init__(self):
        self._connection: aio_pika.RobustConnection | None = None

    async def connect(self) -> None:
        if not self._connection or self._connection.is_closed:
            self._connection = await aio_pika.connect_robust(settings.get_rabbitmq_url)
            logger.info("Connected to RabbitMQ")

    async def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            logger.info("Disconnected from RabbitMQ")

    @asynccontextmanager
    async def get_channel(self) -> AsyncIterator[aio_pika.RobustChannel]:
        await self.connect()
        async with self._connection.channel() as channel:
            yield channel

    async def declare_queue(self, channel: aio_pika.RobustChannel, queue_name: str) -> aio_pika.Queue:
        return await channel.declare_queue(
            queue_name,
            durable=True,
            auto_delete=False
        )

    async def publish_message(
            self,
            queue_name: str,
            message: dict | list | str,
            persistent: bool = True
    ) -> None:
        async with self.get_channel() as channel:
            await self.declare_queue(channel, queue_name)

            if isinstance(message, (dict, list)):
                message_body = json.dumps(message).encode()
            else:
                message_body = str(message).encode()

            delivery_mode = (
                aio_pika.DeliveryMode.PERSISTENT if persistent
                else aio_pika.DeliveryMode.NOT_PERSISTENT
            )

            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=message_body,
                    delivery_mode=delivery_mode
                ),
                routing_key=queue_name
            )
            logger.debug(f"Message published to {queue_name}")

    async def consume_messages(self, queue_name: str) -> AsyncIterator[dict[str, Any]]:
        async with self.get_channel() as channel:
            await channel.set_qos(prefetch_count=10)
            queue = await self.declare_queue(channel, queue_name)

            logger.info(f"Очередь '{queue_name}' готова к получению сообщений")

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    try:
                        async with message.process():
                            data = json.loads(message.body.decode())
                            logger.debug(f"Получено сообщение: {data}")
                            yield data
                    except json.JSONDecodeError as e:
                        logger.error(f"Ошибка декодирования JSON: {e}")
                    except Exception as e:
                        logger.error(f"Ошибка обработки сообщения: {e}")
                        raise