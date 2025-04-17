import enum
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import Enum


class Status(enum.Enum):
    IN_PROGRESS = "еще не сыграла"
    WIN = "выиграла"
    FAIL = "проиграла"

class EventsModel(BaseModel):
    id: int
    bet_amount: Decimal
    status: Status
