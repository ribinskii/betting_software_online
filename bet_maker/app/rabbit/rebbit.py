import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import aio_pika
from app.config import settings

logger = logging.getLogger(__name__)


class RabbitMQSessionManager:
    def __init__(self, prefetch_count: int = 10):
        self.prefetch_count = prefetch_count

    async def consume_messages(self, queue_name: str) -> AsyncIterator[dict[str, Any]]:
        """
        Асинхронный генератор сообщений из очереди RabbitMQ

        :param queue_name: Название очереди
        :yield: Словарь с данными сообщения
        """
        connection = await aio_pika.connect_robust(settings.get_rabbitmq_url)

        try:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=self.prefetch_count)

            queue = await channel.declare_queue(
                queue_name,
                durable=True,
                auto_delete=False
            )

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
        finally:
            await connection.close()