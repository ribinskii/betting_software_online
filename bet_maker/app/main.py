import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
import logging
import aio_pika
import aioredis
from app.db.custom_models import BetAmount, BetOut
from app.db.schemas import Events, Status
from app.db.database import get_session_db, AsyncSessionLocal
from app.config import settings, setup_logging
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.rabbit.queues import events_consumer, status_update_consumer
from app.rabbit.rebbit import RabbitMQSessionManager

setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    consumer_task = asyncio.create_task(events_consumer())
    status_consumer = asyncio.create_task(status_update_consumer())
    yield
    consumer_task.cancel()
    status_consumer.cancel()
    try:
        await asyncio.gather(consumer_task, status_consumer)
    except asyncio.CancelledError:
        print("Consumer остановлен")

app = FastAPI(lifespan=lifespan)

@app.get("/events")
async def get_events(session: AsyncSession = Depends(get_session_db)):
    redis = aioredis.from_url(settings.get_redis_url)
    events_data = await redis.get("available_events")
    if not events_data:
        return []
    events_data = json.loads(events_data)
    print("events_data", events_data)
    available_events = [{"id": event["id"], "odds": event["odds"]} for event in events_data if event["deadline"] < int(datetime.now().timestamp()) and event["status"] == "незавершённое"]
    return available_events

@app.post("/bet")
async def post_bet(bet_amount: BetAmount = Depends(), session: AsyncSession = Depends(get_session_db)):
    try:
        redis = aioredis.from_url(settings.get_redis_url)
        events_data = await redis.get("available_events")
        events_data = json.loads(events_data)
        event = next((e for e in events_data if int(e["id"]) == bet_amount.id), None)

        if not event:
            raise HTTPException(status_code=404, detail="Событие не найдено")

        if event["status"] != "незавершённое":
            raise HTTPException(status_code=400, detail="Ставки на завершенные события невозможны")

        current_time = int(datetime.now().timestamp())
        if event["deadline"] >= current_time:
            raise HTTPException(status_code=400, detail="Дедлайн события истек")

        existing_bet = await session.get(Events, bet_amount.id)
        if existing_bet is not None:
            raise HTTPException(
                status_code=400,
                detail="Ставка с таким ID уже существует"
            )

        new_bet = Events(
            id=bet_amount.id,
            bet_amount=Decimal(str(bet_amount.amount)),
            status=Status.IN_PROGRESS,
        )

        session.add(new_bet)
        await session.commit()
        await session.refresh(new_bet)
        return new_bet

    except ValueError as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await session.rollback()
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при создании ставки: {str(e)}")

@app.get("/bets", response_model=list[BetOut])
async def get_bets(session: AsyncSession = Depends(get_session_db)):
    try:
        stmt = select(Events.id, Events.status)
        result = await session.execute(stmt)
        bets = result.all()

        return [BetOut(id=bet.id, status=bet.status) for bet in bets]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении истории ставок: {str(e)}"
        )


