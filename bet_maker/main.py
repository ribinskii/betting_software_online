import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Path, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from message_brocker import get_session_rabbit
from app.db.session import get_session_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    consumer_task = asyncio.create_task(consumer())
    yield  # Здесь приложение работает
    # Останавливаем consumer при завершении
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        print("Consumer остановлен")

app = FastAPI(lifespan=lifespan)

@app.get("/events")
async def get_events(session: AsyncSession = Depends(get_session_db)):
    pass


async def consumer():
    async for channel in get_session_rabbit():
        await channel.set_qos(prefetch_count=10)  # Ограничиваем количество одновременных задач
        queue = await channel.declare_queue("example_queue", durable=True)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    print(f"Получено: {message.body.decode()}")
                    # Здесь можно добавить логику обработки


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)