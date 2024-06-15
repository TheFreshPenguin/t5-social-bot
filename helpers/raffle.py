from data.models.user import User
from data.models.raffle_entry import RaffleEntry
from data.repositories.raffle import RaffleRepository

from helpers.points import Points

from integrations.loyverse.api import LoyverseApi


class Raffle:
    def __init__(self, loy: LoyverseApi, entries: RaffleRepository, title: str, ticket_price: Points, max_tickets: int = 3, is_active: bool = True):
        self.loy = loy
        self.title = title
        self.ticket_price = ticket_price
        self.max_tickets = max_tickets
        self.is_active = is_active
        self.entries = entries

    def start(self) -> None:
        self.is_active = True

    def stop(self) -> None:
        self.is_active = False

    def buy_ticket(self, user: User) -> None:
        self.loy.remove_points(user, self.ticket_price)
        self.entries.create(user)

    def get_entries(self, user: User) -> list[RaffleEntry]:
        return self.entries.get_by_user(user)

    def has_entries(self, user: User) -> bool:
        return len(self.get_entries(user)) > 0

    def can_enter(self, user: User) -> bool:
        return self.max_tickets > 0 and len(self.get_entries(user)) < self.max_tickets
