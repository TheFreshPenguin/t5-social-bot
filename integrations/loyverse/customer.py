from typing import Optional

from helpers.points import Points


class Customer:
    def __init__(self, customer_id: str, name: str, username: str, points: Points):
        self.customer_id = customer_id
        self.name = name
        self.username = username
        self.points = points

    def to_json(self) -> dict:
        return {
            'id': self.customer_id,
            'name': self.name,
            'note': self.username,
            'total_points': self.points,
        }

    @staticmethod
    def from_json(data: dict) -> Optional["Customer"]:
        username = data.get("note")
        if not username:
            return None

        return Customer(
            customer_id=data.get("id"),
            name=data.get("name"),
            username=username,
            points=Points(data.get("total_points"))
        )