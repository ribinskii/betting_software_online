import asyncio
import json
import logging

import aioredis
from app.config import settings
from app.db.db import AsyncSessionLocal
from app.db.schemas import Events
from app.rabbit.rebbit import RabbitMQSessionManager
from app.rabbit.utils import map_producer_to_consumer_status
from sqlalchemy import select

logger = logging.getLogger(__name__)

async def events_consumer() -> None:
    """
    Потребитель для обработки сообщений из очереди 'test_queue'
    и сохранения данных в Redis
    """
    logger.info("Запуск consumer для обработки событий")

    rabbit_manager = RabbitMQSessionManager(prefetch_count=10)
    redis = aioredis.from_url(settings.get_redis_url)

    try:
        # Правильное использование асинхронного генератора
        message_generator = rabbit_manager.consume_messages("events_queue")
        async for message_data in message_generator:
            try:
                logger.info(f"Получено сообщение: {message_data}")

                await redis.set(
                    "available_events",
                    json.dumps(message_data),
                    ex=3600  # TTL 1 час
                )
                logger.debug("Данные успешно сохранены в Redis")

            except Exception as e:
                logger.error(f"Ошибка обработки сообщения: {e}")

    except asyncio.CancelledError:
        logger.info("Получен сигнал остановки consumer")
    except Exception as e:
        logger.critical(f"Критическая ошибка в consumer: {e}")
    finally:
        await redis.close()
        logger.info("Consumer остановлен")



async def status_update_consumer() -> None:
    logger.info("Запуск консьюмера для обновления статусов событий")

    session = AsyncSessionLocal()
    rabbit_manager = RabbitMQSessionManager(prefetch_count=10)

    try:
        async for data in rabbit_manager.consume_messages("event_status_update_queue"):
            try:
                logger.info(f"Получено обновление статуса: {data}")

                event_id = data["event_id"]
                producer_status_value = data["new_status"]

                try:
                    new_status = map_producer_to_consumer_status(producer_status_value)
                except ValueError:
                    logger.error(f"Неизвестный статус: {producer_status_value}")
                    continue

                # Проверяем существование события
                result = await session.execute(
                    select(Events).where(Events.id == event_id)
                )
                event = result.scalar_one_or_none()

                if not event:
                    logger.error(f"Событие с ID {event_id} не найдено")
                    continue

                # Обновляем статус
                event.status = new_status
                await session.commit()
                logger.info(f"Статус события {event_id} обновлен на {new_status}")

            except KeyError as e:
                logger.error(f"Отсутствует обязательное поле в сообщении: {e}")
            except Exception as e:
                logger.error(f"Ошибка обработки сообщения: {e}")
                await session.rollback()

    except Exception as e:
        logger.error(f"Ошибка в консьюмере статусов: {e}")
    finally:
        await session.close()