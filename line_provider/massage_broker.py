import aio_pika
from config import settings

async def get_session_rabbit():
    print("Подключение к RabbitMQ...")
    connection = await aio_pika.connect_robust(settings.get_rabbitmq_url)
    print("connection", connection)
    async with connection:
        print("Подключение к RabbitMQ установлено")
        channel = await connection.channel()  # Создаем канал
        yield channel  # Возвращаем канал для использования
