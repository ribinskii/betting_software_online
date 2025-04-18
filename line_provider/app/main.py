import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routers_bind import router_base
from app.config import settings, setup_logging
from app.db.db import engine
from app.rebbit.queues import events_producer

setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Lifespan_запущен")
    task = asyncio.create_task(events_producer())
    yield
    task.cancel()
    await engine.dispose()
    try:
        await task
    except asyncio.CancelledError:
        print("Фоновая задача остановлена")


app = FastAPI(lifespan=lifespan, title="line_provider", description="API provides information about events that ca be bet on", version="0.0.1")

app.include_router(router_base)
