from decimal import Decimal

from pydantic import BaseModel, validator


class BetAmount(BaseModel):
    id: int
    amount: Decimal

    # Валидация суммы ставки
    @validator("amount")
    def validate_amount(cls, amount):
        if amount <= 0:
            raise ValueError("Сумма ставки должна быть положительной")
        if abs(amount.as_tuple().exponent) > 2:
            raise ValueError("Сумма должна иметь не более 2 знаков после запятой")
        return amount