import asyncio
import json
import logging
from contextlib import asynccontextmanager

import aio_pika
import uvicorn
from app.db.models import Events, EventsModel, Status
from app.db.session import AsyncSessionLocal, get_session_db
from config import settings
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Lifespan_запущен")
    task = asyncio.create_task(producer())
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
        session: AsyncSession = Depends(get_session_db)
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
        connection = await aio_pika.connect_robust(settings.get_rabbitmq_url)
        async with connection:
            channel = await connection.channel()
            queue = await channel.declare_queue("event_status_updates", durable=True)

            message_body = json.dumps({
                "event_id": event_id,
                "new_status": new_status.value
            }).encode()

            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=message_body,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key="event_status_updates"
            )

        return {"message": "Status updated successfully", "event_id": event_id, "new_status": new_status.value}

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating event status: {str(e)}")


async def send_message(channel, queue_name, data: list):
    await channel.default_exchange.publish(
        aio_pika.Message(body=json.dumps(data).encode()),
        routing_key=queue_name,
    )


async def producer():
    session = AsyncSessionLocal()

    try:
        connection = await aio_pika.connect_robust(settings.get_rabbitmq_url)
        queue_name = "test_queue"


        async with connection:
            channel = await connection.channel(publisher_confirms=False)
            print("Producer: подключение к RabbitMQ установлено")
            queue = await channel.declare_queue(
                queue_name,
                durable=True,  # Сохранять сообщения при перезапуске RabbitMQ
                auto_delete=False  # Не удалять очередь при отключении клиента
            )
            print(f"Очередь '{queue_name}' создана/подключена")

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

                    await send_message(channel, queue_name, events_data)
                except Exception as e:
                    await session.rollback()
                    logging.error(f"Error: {e}")

                await asyncio.sleep(10)
    finally:
        await session.close()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
