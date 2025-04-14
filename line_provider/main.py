import logging
from contextlib import asynccontextmanager

import aio_pika
import uvicorn
from fastapi import FastAPI, Path, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Events, EventsModel
from app.db.session import get_session_db
import asyncio
from datetime import datetime

from config import settings
from massage_broker import get_session_rabbit

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Lifespan_запущен")
    await producer()
    yield


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




async def producer():
    print("settings.get_rabbitmq_url", settings.get_rabbitmq_url)
    connection = await aio_pika.connect_robust(settings.get_rabbitmq_url, timeout=10)

    queue_name = "test_queue"

    async with connection:
        routing_key = "test_queue"
        channel = await connection.channel()
        print("Producer: подключение к RabbitMQ установлено")

        await channel.default_exchange.publish(
            aio_pika.Message(body=f"Hello {routing_key}".encode()),
            routing_key=routing_key,
        )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
