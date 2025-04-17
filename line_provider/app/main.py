import asyncio
import json
import logging
from contextlib import asynccontextmanager

import aio_pika
from app.db.models import EventsModel, Status
from app.db.schemas import Events
from app.db.database import get_session_db, AsyncSessionLocal
from app.config import settings, setup_logging
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.rebbit.queues import events_producer
from app.rebbit.rebbit import RabbitMQSessionManager

setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Lifespan_запущен")
    task = asyncio.create_task(events_producer())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("Фоновая задача остановлена")


app = FastAPI(lifespan=lifespan)

@app.get("/events")
async def get_events(session: AsyncSession = Depends(get_session_db)):
    query = select(Events)
    result = await session.execute(query)
    events = result.scalars().all()
    print(events)
    return events

@app.post("/event")
async def create_event(event: EventsModel=Depends(), session: AsyncSession = Depends(get_session_db)):
    new_event = Events(
        odds=event.odds,
        deadline=event.deadline,
        status=event.status,
    )
    session.add(new_event)
    await session.commit()
    await session.refresh(new_event)
    return new_event

@app.delete("/event/{event_id}")
async def delete_event(event_id: int, session: AsyncSession = Depends(get_session_db)):
    result = await session.execute(select(Events).where(Events.id == event_id))
    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    await session.delete(event)
    await session.commit()

    return {"detail": f"Event with id {event_id} deleted successfully"}

@app.patch("/event/{event_id}/status")
async def update_event_status(
        event_id: int,
        new_status: Status,
        session: AsyncSession = Depends(get_session_db),
        rabbitmq: RabbitMQSessionManager = Depends(RabbitMQSessionManager)
):
    try:
        # 1. Проверяем существование события
        result = await session.execute(select(Events).where(Events.id == event_id))
        event = result.scalar_one_or_none()

        if event is None:
            raise HTTPException(status_code=404, detail="Event not found")

        # 2. Обновляем статус
        await session.execute(
            update(Events)
            .where(Events.id == event_id)
            .values(status=new_status)
        )
        await session.commit()

        # 3. Отправляем обновление в RabbitMQ
        await rabbitmq.publish_message(
            queue_name="event_status_update_queue",
            message={
                "event_id": event_id,
                "new_status": new_status.value
            }
        )

        return {"message": "Status updated successfully", "event_id": event_id, "new_status": new_status.value}

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating event status: {str(e)}")
