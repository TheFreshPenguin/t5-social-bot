from typing import Optional, Union
from datetime import date, datetime

from data.models.user import User


class UserRepository:
    def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        pass

    def get_by_telegram_name(self, telegram_name: str) -> Optional[User]:
        pass

    def get_by_birthday(self, birthday: Union[str, date, datetime]) -> list[User]:
        pass

    def get_by_loyverse_id(self, loyverse_id: str) -> Optional[User]:
        pass

    def search(self, query: str) -> set[User]:
        pass

    def save(self, user: User) -> None:
        pass

    def save_all(self, users: list[User]) -> None:
        pass
