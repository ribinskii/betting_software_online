import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal

import aio_pika
import aioredis
import uvicorn
from app.db.custom_models import BetAmount, BetOut
from app.db.models import Events, Status, LineProviderStatus
from app.db.session import get_session_db, AsyncSessionLocal
from config import settings
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def lifespan(app: FastAPI):
    consumer_task = asyncio.create_task(consumer())
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

async def consumer() -> None:
    print("Началось подключение к RabbitMQ")
    try:
        connection = await aio_pika.connect_robust(
            settings.get_rabbitmq_url,
        )
        print("Успешное подключение к RabbitMQ")

        queue_name = "test_queue"

        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=10)

            # 1. Создаем очередь без auto_delete
            queue = await channel.declare_queue(
                queue_name,
                durable=True,  # Сохранять очередь после перезапуска
                auto_delete=False  # Не удалять при отключении
            )

            print(f"Очередь '{queue_name}' готова к получению сообщений")

            # 2. Явно привязываем к exchange (если нужно)
            # exchange = await channel.declare_exchange("direct", auto_delete=False)
            # await queue.bind(exchange, routing_key=queue_name)

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    try:
                        async with message.process():
                            available_events = json.loads(message.body.decode())
                            print(f"Получено сообщение: {available_events}")
                            redis = aioredis.from_url(settings.get_redis_url)
                            await redis.set("available_events", json.dumps(available_events))

                    except Exception as e:
                        print(f"Ошибка обработки сообщения: {e}")
                        # Можно добавить логику повторной обработки

    except Exception as e:
        print(f"Ошибка в consumer: {e}")
        # Здесь можно добавить логику переподключения

def map_producer_to_consumer_status(producer_status):
    mapping = {
        "незавершённое": Status.IN_PROGRESS,
        "завершено выигрышем первой команды": Status.WIN,
        "завершено выигрышем второй команды": Status.FAIL
    }
    return mapping.get(producer_status, Status.IN_PROGRESS)
async def status_update_consumer() -> None:
    print("Запуск консьюмера для обновления статусов событий")
    session = AsyncSessionLocal()

    try:
        connection = await aio_pika.connect_robust(
            settings.get_rabbitmq_url,
        )
        print("Успешное подключение к RabbitMQ для консьюмера статусов")

        queue_name = "event_status_updates"

        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=10)

            queue = await channel.declare_queue(
                queue_name,
                durable=True,
                auto_delete=False
            )

            print(f"Очередь '{queue_name}' готова к получению сообщений")

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    try:
                        async with message.process():
                            data = json.loads(message.body.decode())
                            print(f"Получено обновление статуса: {data}")

                            # Обновляем статус в базе данных
                            event_id = data["event_id"]
                            producer_status_value = data["new_status"]

                            # Преобразуем статус продюсера в статус консьюмера
                            try:
                                new_status = map_producer_to_consumer_status(producer_status_value)
                            except ValueError:
                                print(f"Неизвестный статус: {producer_status_value}")
                                continue
                            # Проверяем существование события
                            result = await session.execute(
                                select(Events).where(Events.id == event_id)
                            )
                            event = result.scalar_one_or_none()

                            if not event:
                                print(f"Событие с ID {event_id} не найдено")
                                continue
                            # Обновляем статусevent
                            event.status = new_status
                            await session.commit()
                            print(f"Статус события {event_id} обновлен на {new_status}")

                    except json.JSONDecodeError as e:
                        print(f"Ошибка декодирования JSON: {e}")
                    except KeyError as e:
                        print(f"Отсутствует обязательное поле в сообщении: {e}")
                    except Exception as e:
                        print(f"Ошибка обработки сообщения: {e}")
                        await session.rollback()

    except Exception as e:
        print(f"Ошибка в консьюмере статусов: {e}")
    finally:
        await session.close()
