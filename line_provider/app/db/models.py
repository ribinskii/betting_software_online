import enum
from decimal import Decimal

from pydantic import BaseModel


class Status(enum.Enum):
    IN_PROGRESS = "незавершённое"
    TEAM_ONE_WON = "завершено выигрышем первой команды"
    TEAM_TWO_WON = "завершено выигрышем второй команды"

class EventsModel(BaseModel):
    id: int | None = None
    odds: Decimal
    deadline: int
    status: Status
