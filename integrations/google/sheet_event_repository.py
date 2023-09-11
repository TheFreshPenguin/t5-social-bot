import pytz

from datetime import date, datetime, timedelta
from typing import List, Union
from itertools import groupby

from readerwriterlock import rwlock

from data.repositories.event import EventRepository
from data.models.event import Event

from integrations.google.sheet_database import GoogleSheetDatabase


class GoogleSheetEventRepository(EventRepository):
    def __init__(self, database: GoogleSheetDatabase, timezone: pytz.timezone = None):
        self.timezone = timezone

        # The repository data can be read and refreshed from different threads,
        # so any data operation needs to be protected
        self.lock = rwlock.RWLockWrite()

        self.events = []
        self.events_by_date = {}

        database.events.subscribe(self.__load)

    def get_all_events(self) -> List[Event]:
        with self.lock.gen_rlock():
            return self.events

    def get_events_on(self, on_date: Union[date, datetime]) -> List[Event]:
        with self.lock.gen_rlock():
            return self.events_by_date.get(on_date.strftime('%Y-%m-%d'), [])

    def __load(self, raw_data: list) -> None:
        with self.lock.gen_wlock():
            self.events = [Event(
                name=row.get('event', '').strip(),
                start_date=self.__parse_datetime(row.get('date', '').strip() + ' ' + row.get('time', '').strip()),
                host=row.get('host', '').strip(),
                description=row.get('description', '').strip(),
            ) for row in raw_data]

            self.events.sort(key=lambda event: event.start_date)
            grouped_events = groupby(self.events, key=lambda event: event.start_date.strftime('%Y-%m-%d'))
            self.events_by_date = {key: list(items) for key, items in grouped_events}

            # We assume that main events have a duration of 3 hours
            for key, events in self.events_by_date.items():
                main_event = events[-1]
                main_event.end_date = main_event.start_date + timedelta(hours=3)

    def __parse_datetime(self, datestr: str) -> datetime:
        return self.timezone.localize(datetime.strptime(datestr, '%Y-%m-%d %H:%M'))
