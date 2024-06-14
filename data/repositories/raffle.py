from data.models.user import User
from data.models.raffle_entry import RaffleEntry


class RaffleRepository:
    def get_by_user(self, user: User) -> list[RaffleEntry]:
        pass

    def list_by_user(self) -> dict[str, list[RaffleEntry]]:
        pass

    def create(self, user: User) -> RaffleEntry:
        pass
