from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, declared_attr, DeclarativeMeta
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from stringcase import snakecase

from config import settings

DATABASE_URL = settings.get_db_url

engine = create_async_engine(url=DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return snakecase(cls.__name__)