from decimal import Decimal

from sqlalchemy import Enum, Numeric
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column
from stringcase import snakecase

from app.config import settings
from app.db.models import Status

DATABASE_URL = settings.get_db_url

engine = create_async_engine(url=DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return snakecase(cls.__name__)

class Events(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, nullable=False)
    bet_amount: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    status: Mapped[Status] = mapped_column(nullable=False)
