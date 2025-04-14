import enum
from decimal import Decimal
from pydantic import BaseModel
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Numeric, Integer, Enum

from app.db.database import Base

class Status(enum.Enum):
    IN_PROGRESS = "еще не сыграла"
    WIN = "выиграла"
    FAIL = "проиграла"

class EventsModel(BaseModel):
    id: int | None = None
    bet_amount: Decimal
    status: Status

class Events(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, nullable=False)
    bet_amount: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    status: Mapped[Status] = mapped_column(Enum(Status), nullable=False) # можно ли удалить Enum(Status)?
