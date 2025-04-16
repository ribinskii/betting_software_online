import enum
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import Enum, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Status(enum.Enum):
    IN_PROGRESS = "незавершённое"
    TEAM_ONE_WON = "завершено выигрышем первой команды"
    TEAM_TWO_WON = "завершено выигрышем второй команды"

class EventsModel(BaseModel):
    id: int | None = None
    odds: Decimal
    deadline: int
    status: Status

class Events(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, nullable=False)
    odds: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    deadline: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[Status] = mapped_column(Enum(Status), nullable=False) # можно ли удалить Enum(Status)?
