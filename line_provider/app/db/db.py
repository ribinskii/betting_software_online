from collections.abc import AsyncGenerator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.get_db_url, echo=False)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise exc
    finally:
        await session.close()
