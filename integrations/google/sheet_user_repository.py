from typing import Optional, Union
from itertools import groupby
from datetime import date, datetime

from readerwriterlock import rwlock

from data.repositories.user import UserRepository
from data.models.user import User

from integrations.google.sheet_database import GoogleSheetDatabase


class GoogleSheetUserRepository(UserRepository):
    def __init__(self, database: GoogleSheetDatabase):
        self.users = []
        self.users_by_telegram_id = {}
        self.users_by_telegram_name = {}
        self.users_by_birthday = {}

        # The repository data can be read and refreshed from different threads,
        # so any data operation needs to be protected
        self.lock = rwlock.RWLockWrite()

        database.users.subscribe(self.__load)

    def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        return self.users_by_telegram_id.get(telegram_id)

    def get_by_telegram_name(self, telegram_name: str) -> Optional[User]:
        return self.users_by_telegram_name.get(telegram_name)

    def get_by_birthday(self, birthday: Union[str, date, datetime]) -> list[User]:
        date_string = birthday if isinstance(birthday, str) else birthday.strftime('%m-%d')
        return self.users_by_birthday.get(date_string, [])

    def search(self, query: str) -> set[User]:
        # Upcoming - will be used to help with finding the right person to donate to
        pass

    def save(self, user: User) -> None:
        # Upcoming - will be used to keep track of who talked to the bot
        pass

    def __load(self, raw_data: list) -> None:
        with self.lock.gen_wlock():
            self.users = [User(
                full_name=row.get('full_name', '').strip(),
                aliases=GoogleSheetUserRepository.__parse_aliases(row.get('aliases', '')),
                telegram_username=row.get('telegram_username', '').strip(),
                birthday=row.get('birthday', ''),
                telegram_id=GoogleSheetUserRepository.__parse_int(row.get('telegram_id', '')),
                loyverse_id=row.get('loyverse_id', '').strip(),
            ) for row in raw_data]

            self.users_by_telegram_id = {user.telegram_id: user for user in self.users if user.telegram_id}
            self.users_by_telegram_name = {user.telegram_username: user for user in self.users if user.telegram_username}

            users_with_birthday = [user for user in self.users if user.birthday]
            sorted_birthdays = sorted(users_with_birthday, key=lambda user: user.birthday)
            self.users_by_birthday = {key: list(group) for key, group in groupby(sorted_birthdays, key=lambda user: user.birthday)}

    @staticmethod
    def __parse_int(int_string: str) -> Optional[int]:
        try:
            return int(int_string.strip())
        except ValueError:
            return None

    @staticmethod
    def __parse_aliases(alias_string: str) -> list[str]:
        clean = [alias.strip() for alias in alias_string.split(',')]
        return [alias for alias in clean if alias]
