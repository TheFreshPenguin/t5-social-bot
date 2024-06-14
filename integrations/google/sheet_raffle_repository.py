import pytz
import random

from typing import Optional
from itertools import groupby
from datetime import datetime

from readerwriterlock import rwlock

from data.repositories.raffle import RaffleRepository
from data.models.user import User
from data.models.raffle_entry import RaffleEntry

from integrations.google.sheet_database import GoogleSheetDatabase

countries = [
    'Albania',
    'Austria',
    'Belgium',
    'Croatia',
    'Czech Republic',
    'Denmark',
    'England',
    'France',
    'Georgia',
    'Germany',
    'Hungary',
    'Italy',
    'Netherlands',
    'Poland',
    'Portgal',
    'Romania',
    'Scotland',
    'Serbia',
    'Slovakia',
    'Slovenia',
    'Spain',
    'Switzerland',
    'Turkey',
    'Ukraine',
]


class GoogleSheetRaffleRepository(RaffleRepository):
    def __init__(self, database: GoogleSheetDatabase, timezone: pytz.timezone = None):
        self.timezone = timezone

        self.entries: list[RaffleEntry] = []
        self.entries_by_full_name: dict[str, list[RaffleEntry]] = {}

        # The repository data can be read and refreshed from different threads,
        # so any data operation needs to be protected
        self.lock = rwlock.RWLockWrite()

        self.database = database
        self.database.raffle.subscribe(self._load)

    def get_by_user(self, user: User) -> list[RaffleEntry]:
        with self.lock.gen_rlock():
            return self.entries_by_full_name.get(user.full_name, [])

    def list_by_user(self) -> dict[str, list[RaffleEntry]]:
        with self.lock.gen_rlock():
            return self.entries_by_full_name.copy()

    def create(self, user: User) -> RaffleEntry:
        with self.lock.gen_wlock():
            entry = RaffleEntry(
                full_name=user.full_name,
                created_at=datetime.now(tz=self.timezone),
                country=random.choice(countries)
            )

            self.entries.append(entry)
            if entry.full_name in self.entries_by_full_name:
                self.entries_by_full_name[entry.full_name].append(entry)
            else:
                self.entries_by_full_name[entry.full_name] = [entry]

            self.database.add_raffle_entry(self._to_row(entry))

            return entry

    def _load(self, raw_data: list[dict[str, str]]) -> None:
        with self.lock.gen_wlock():
            raw_entries = [self._from_row(row) for row in raw_data]
            self.entries = [entry for entry in raw_entries if entry]

            sorted_entries = sorted(self.entries, key=lambda entry: entry.full_name)
            self.entries_by_full_name = {key: list(group) for key, group in groupby(sorted_entries, key=lambda entry: entry.full_name)}

    def _from_row(self, row: dict[str, str]) -> Optional[RaffleEntry]:
        full_name = row.get('champion_name', '').strip()
        if not full_name:
            return None

        country = row.get('country', '').strip()
        if not country:
            return None

        return RaffleEntry(
            full_name=full_name,
            created_at=self._parse_datetime(row.get('date', '').strip()),
            country=country,
        )

    @staticmethod
    def _to_row(entry: RaffleEntry) -> dict[str, str]:
        return {
            'champion_name': entry.full_name,
            'date': entry.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'country': entry.country,
        }

    def _parse_datetime(self, datetime_string: str) -> Optional[datetime]:
        try:
            return self.timezone.localize(datetime.strptime(datetime_string, '%Y-%m-%d %H:%M:%S'))
        except ValueError:
            return None
