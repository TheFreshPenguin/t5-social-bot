from decimal import *
from typing import Union

from helpers.exceptions import UserFriendlyError


class Points:
    def __init__(self, amount: Union[str, int, float, Decimal]):
        try:
            self.amount = Decimal(str(amount))
            if not (self.amount.is_normal() or self.amount.is_zero()):
                raise ValueError('Invalid number')
        except (InvalidOperation, ValueError) as error:
            raise UserFriendlyError('The number of points must be ... a number 😬') from error

    def is_positive(self) -> bool:
        return self.amount > Decimal(0)

    def is_negative(self) -> bool:
        return self.amount < Decimal(0)

    def is_zero(self) -> bool:
        return self.amount.is_zero()

    def add(self, delta: "Points") -> "Points":
        return Points(self.amount + delta.amount)

    def subtract(self, delta: "Points") -> "Points":
        return Points(self.amount - delta.amount)

    def to_json(self) -> float:
        return float(self.amount)
