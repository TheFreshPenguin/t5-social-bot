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

    def __add__(self, other) -> "Points":
        return Points(self.amount + other.amount)

    def __sub__(self, other) -> "Points":
        return Points(self.amount - other.amount)

    def __eq__(self, other):
        return self.amount == other.amount

    def __lt__(self, other):
        return self.amount < other.amount

    def __le__(self, other):
        return self.amount <= other.amount

    def __gt__(self, other):
        return self.amount > other.amount

    def __ge__(self, other):
        return self.amount >= other.amount

    def __str__(self):
        return str(self.amount)

    def __repr__(self):
        return str(self)

    def is_positive(self) -> bool:
        return self.amount > Decimal(0)

    def is_negative(self) -> bool:
        return self.amount < Decimal(0)

    def is_zero(self) -> bool:
        return self.amount.is_zero()

    def to_integral(self) -> "Points":
        return Points(self.amount.to_integral(rounding=ROUND_FLOOR))

    def to_json(self) -> float:
        return float(self.amount)
