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
        self.users_search = {}

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
        query = query.lower()

        # A direct match is a successful prefix search; this is usually what we want
        if query in self.users_search:
            return self.users_search[query]

        # No direct matches -> do a full search
        results = set()
        for key, users in self.users_search.items():
            if query in key:
                results |= users

        return results

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

            self.users_search = {}
            # Complete telegram username
            self.__add_to_search({user.telegram_username.lower(): user for user in self.users})
            for user in self.users:
                # Complete alias list
                self.__add_to_search({alias.lower(): user for alias in user.aliases})
                # First name from full name
                self.__add_to_search({user.first_name.lower(): user})
            # Complete full name
            self.__add_to_search({user.full_name.lower(): user for user in self.users if user.full_name})

            self.__merge_search_prefixes()

    # E.g. The entry for Alex will match Alex Uzan, Alexandru Ivanciu, and Alexandra Tudor
    # Without this, it would only match Alex Uzan
    def __merge_search_prefixes(self) -> None:
        sorted_keys = list(self.users_search.keys())
        sorted_keys.sort()

        prefix_i = 0
        current_i = 1

        while current_i < len(sorted_keys):
            prefix = sorted_keys[prefix_i]
            key = sorted_keys[current_i]
            if key.startswith(prefix):
                self.users_search[prefix] |= self.users_search[sorted_keys[current_i]]
                current_i = current_i + 1
            else:
                prefix_i = prefix_i + 1
                current_i = prefix_i + 1

    def __add_to_search(self, entries: dict[str, User]) -> None:
        for key, user in entries.items():
            if key in self.users_search:
                self.users_search[key].add(user)
            else:
                self.users_search[key] = {user}

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
