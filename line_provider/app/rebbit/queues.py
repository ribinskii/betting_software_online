import asyncio
import json
import logging
from contextlib import asynccontextmanager

import aio_pika
from app.db.models import EventsModel, Status
from app.db.schemas import Events
from app.db.db import get_db, AsyncSessionLocal
from app.config import settings, setup_logging
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.rebbit.rebbit import RabbitMQSessionManager

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
