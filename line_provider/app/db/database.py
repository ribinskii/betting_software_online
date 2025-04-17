from collections.abc import AsyncGenerator

from app.config import settings
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

engine = create_async_engine(settings.get_db_url, echo=False)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession  # Явно указываем класс сессии
)

async def get_session_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Генератор асинхронных сессий базы данных.
    """
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise exc
    finally:
        await session.close()
