import asyncio
import logging

from app.db.db import AsyncSessionLocal
from app.db.schemas import Events
from app.rabbit.rabbit import RabbitMQSessionManager
from sqlalchemy import select

logger = logging.getLogger(__name__)

async def events_producer():
    session = AsyncSessionLocal()
    rabbitmq = RabbitMQSessionManager()

    try:
        while True:
            try:
                result = await session.execute(select(Events))
                events = result.scalars().all()

                events_data = [{
                    "id": event.id,
                    "odds": str(event.odds),
                    "deadline": event.deadline,
                    "status": event.status.value
                } for event in events]

                await rabbitmq.publish_message(
                    queue_name="events_queue",
                    message=events_data
                )
                logger.info(f"Published {len(events_data)} events to RabbitMQ")

            except Exception as e:
                await session.rollback()
                logger.error(f"Error in producer: {e}")

            await asyncio.sleep(10)
    finally:
        await session.close()
        await rabbitmq.close()
