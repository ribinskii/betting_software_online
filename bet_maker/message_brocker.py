import aio_pika
from config import settings


async def get_session_rabbit():
    connection = await aio_pika.connect_robust(settings.get_db_url)
    async with connection:
        channel = await connection.channel()  # Создаем канал
        yield channel  # Возвращаем канал для использования



