from app.db.models import Status
from app.config import settings
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, declared_attr
from stringcase import snakecase
from decimal import Decimal

from sqlalchemy import Numeric
from sqlalchemy.orm import Mapped, mapped_column


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
    odds: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    deadline: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[Status] = mapped_column(nullable=False)
