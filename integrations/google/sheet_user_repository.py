import pytz

from typing import Optional, Union
from itertools import groupby
from datetime import date, datetime

from readerwriterlock import rwlock

from data.repositories.user import UserRepository
from data.models.user import User
from data.models.user_role import UserRole

from integrations.google.handle import Handle
from integrations.google.sheet_database import GoogleSheetDatabase

UserHandle = Handle[User]


class GoogleSheetUserRepository(UserRepository):
    def __init__(self, database: GoogleSheetDatabase, timezone: pytz.timezone = None):
        self.timezone = timezone

        self.users: list[UserHandle] = []
        self.users_by_full_name: dict[str, UserHandle] = {}
        self.users_by_telegram_id: dict[int, UserHandle] = {}
        self.users_by_telegram_name: dict[str, UserHandle] = {}
        self.users_by_birthday: dict[str, list[UserHandle]] = {}
        self.users_by_loyverse_id: dict[str, list[UserHandle]] = {}
        self.users_search: dict[str, set[UserHandle]] = {}

        # The repository data can be read and refreshed from different threads,
        # so any data operation needs to be protected
        self.lock = rwlock.RWLockWrite()

        self.database = database
        database.users.subscribe(self._load)

    def get_by_full_name(self, full_name: str) -> Optional[User]:
        with self.lock.gen_rlock():
            return self.users_by_full_name.get(full_name, Handle(None)).inner

    def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        with self.lock.gen_rlock():
            return self.users_by_telegram_id.get(telegram_id, Handle(None)).inner

    def get_by_telegram_name(self, telegram_name: str) -> Optional[User]:
        with self.lock.gen_rlock():
            return self.users_by_telegram_name.get(telegram_name, Handle(None)).inner

    def get_by_birthday(self, birthday: Union[str, date, datetime]) -> list[User]:
        with self.lock.gen_rlock():
            date_string = birthday if isinstance(birthday, str) else birthday.strftime('%m-%d')
            return Handle.unwrap_list(self.users_by_birthday.get(date_string, []))

    def get_by_loyverse_id(self, loyverse_id: str) -> Optional[User]:
        with self.lock.gen_rlock():
            return self.users_by_loyverse_id.get(loyverse_id, Handle(None)).inner

    def search(self, query: str) -> set[User]:
        with self.lock.gen_rlock():
            query = query.lower()

            # A direct match is a successful prefix search; this is usually what we want
            if query in self.users_search:
                return Handle.unwrap_set(self.users_search[query])

            # No direct matches -> do a full search
            results: set[UserHandle] = set()
            for key, handles in self.users_search.items():
                if query in key:
                    results |= handles

            return Handle.unwrap_set(results)

    def save(self, user: User) -> None:
        self.save_all([user])

    def save_all(self, users: list[User]) -> None:
        if not users:
            return

        with self.lock.gen_wlock():
            diff_data = {}
            for user in users:
                # Only existing users are saved
                handle = self.users_by_full_name[user.full_name]
                if not handle:
                    continue

                # Only users with data changes will be saved
                diff = GoogleSheetUserRepository._diff(handle.inner, user)
                if not diff:
                    continue

                # Update the repository directly
                handle.inner = user
                # Queue the user for update in the database
                diff_data[user.full_name] = diff

            # Save changes to the database as well
            if diff_data:
                self.database.save_users('full_name', diff_data)

    def _load(self, raw_data: list[dict[str, str]]) -> None:
        with self.lock.gen_wlock():
            raw_users = [self._from_row(row) for row in raw_data]
            self.users = [UserHandle(user) for user in raw_users if user]

            self.users_by_full_name = {handle.inner.full_name: handle for handle in self.users if handle.inner}
            self.users_by_telegram_id = {handle.inner.telegram_id: handle for handle in self.users if handle.inner.telegram_id}
            self.users_by_telegram_name = {handle.inner.telegram_username: handle for handle in self.users if handle.inner.telegram_username}
            self.users_by_loyverse_id = {handle.inner.loyverse_id: handle for handle in self.users if handle.inner.loyverse_id}

            users_with_birthday = [handle for handle in self.users if handle.inner.birthday]
            sorted_birthdays = sorted(users_with_birthday, key=lambda handle: handle.inner.birthday)
            self.users_by_birthday = {key: list(group) for key, group in groupby(sorted_birthdays, key=lambda handle: handle.inner.birthday)}

            self.users_search = {}
            # Complete telegram username
            self._add_to_search({handle.inner.telegram_username.lower(): handle for handle in self.users if handle.inner.telegram_username})
            for handle in self.users:
                # Complete alias list
                self._add_to_search({alias.lower(): handle for alias in handle.inner.aliases})
                # First name from full name
                self._add_to_search({handle.inner.first_name.lower(): handle})
            # Complete full name
            self._add_to_search({handle.inner.full_name.lower(): handle for handle in self.users if handle.inner})

            self._merge_search_prefixes()

    # E.g. The entry for Alex will match Alex Uzan, Alexandru Ivanciu, and Alexandra Tudor
    # Without this, it would only match Alex Uzan
    def _merge_search_prefixes(self) -> None:
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

    def _add_to_search(self, entries: dict[str, UserHandle]) -> None:
        for key, user in entries.items():
            if key in self.users_search:
                self.users_search[key].add(user)
            else:
                self.users_search[key] = {user}

    def _from_row(self, row: dict[str, str]) -> Optional[User]:
        # The full name is required, because we use it for saving
        full_name = row.get('full_name', '').strip()
        if not full_name:
            return None

        return User(
            full_name=full_name,
            aliases=GoogleSheetUserRepository._parse_aliases(row.get('aliases', '')),
            role=GoogleSheetUserRepository._parse_user_role(row.get('role', '')),
            telegram_username=row.get('telegram_username', '').strip(),
            birthday=row.get('birthday', ''),
            telegram_id=GoogleSheetUserRepository._parse_int(row.get('telegram_id', '')),
            loyverse_id=row.get('loyverse_id', '').strip(),
            last_private_chat=self._parse_datetime(row.get('last_private_chat', '').strip()),
            last_visit=self._parse_datetime(row.get('last_visit', '').strip()),
            recent_visits=GoogleSheetUserRepository._parse_int(row.get('recent_visits', '')) or 0,
        )

    @staticmethod
    def _to_row(user: User) -> dict[str, str]:
        return {
            'full_name': user.full_name,
            'aliases': ','.join(user.aliases),
            'role': user.role.value.capitalize(),
            'telegram_username': user.telegram_username,
            'birthday': user.birthday,
            'telegram_id': user.telegram_id,
            'loyverse_id': user.loyverse_id,
            'last_private_chat': user.last_private_chat.strftime('%Y-%m-%d %H:%M:%S') if user.last_private_chat else None,
            'last_visit': user.last_visit.strftime('%Y-%m-%d %H:%M:%S') if user.last_visit else None,
            'recent_visits': user.recent_visits,
        }

    @staticmethod
    def _diff(a: User, b: User) -> dict[str, str]:
        a_row = GoogleSheetUserRepository._to_row(a)
        b_row = GoogleSheetUserRepository._to_row(b)
        return {k: v for k, v in b_row.items() if a_row[k] != b_row[k]}

    def _parse_datetime(self, datetime_string: str) -> Optional[datetime]:
        try:
            return self.timezone.localize(datetime.strptime(datetime_string, '%Y-%m-%d %H:%M:%S'))
        except ValueError:
            return None

    @staticmethod
    def _parse_int(int_string: str) -> Optional[int]:
        try:
            return int(int_string.strip())
        except ValueError:
            return None

    @staticmethod
    def _parse_aliases(alias_string: str) -> list[str]:
        clean = [alias.strip() for alias in alias_string.split(',')]
        return [alias for alias in clean if alias]

    @staticmethod
    def _parse_user_role(user_role_string: str) -> Optional[UserRole]:
        try:
            return UserRole(user_role_string.strip().lower())
        except ValueError:
            return UserRole.CHAMPION
