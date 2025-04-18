import asyncio
from contextlib import asynccontextmanager
import logging

import aioredis

from app.api.routers_bind import router_base
from app.config import settings, setup_logging
from fastapi import Depends, FastAPI, HTTPException

from app.rabbit.queues import events_consumer, status_update_consumer

setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = await aioredis.from_url(settings.get_redis_url)
    app.state.redis = redis

    consumer_task = asyncio.create_task(events_consumer())
    status_consumer = asyncio.create_task(status_update_consumer())

    yield
    consumer_task.cancel()
    status_consumer.cancel()
    await redis.close()
    try:
        await asyncio.gather(consumer_task, status_consumer)
    except asyncio.CancelledError:
        print("Consumer остановлен")

app = FastAPI(lifespan=lifespan, title="bet_maker", description="API responsible for delivering bets on events by users", version="0.0.1")


app.include_router(router_base)