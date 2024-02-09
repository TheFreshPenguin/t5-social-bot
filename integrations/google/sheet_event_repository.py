import pytz

from datetime import date, datetime, timedelta
from typing import Union, Optional
from itertools import groupby

from readerwriterlock import rwlock

from data.repositories.event import EventRepository
from data.models.event import Event

from integrations.google.handle import Handle
from integrations.google.sheet_database import GoogleSheetDatabase

EventHandle = Handle[Event]


class GoogleSheetEventRepository(EventRepository):
    def __init__(self, database: GoogleSheetDatabase, timezone: pytz.timezone = None):
        self.timezone = timezone

        # The repository data can be read and refreshed from different threads,
        # so any data operation needs to be protected
        self.lock = rwlock.RWLockWrite()

        self.events: list[EventHandle] = []
        self.events_by_date: dict[date, list[EventHandle]] = {}

        database.events.subscribe(self._load)

    def get_all_events(self) -> list[Event]:
        with self.lock.gen_rlock():
            return EventHandle.unwrap_list(self.events)

    def get_events_on(self, on_date: Union[date, datetime]) -> list[Event]:
        real_date = on_date if type(on_date) is date else on_date.date()
        with self.lock.gen_rlock():
            return EventHandle.unwrap_list(self.events_by_date.get(real_date, []))

    def _load(self, raw_data: list) -> None:
        with self.lock.gen_wlock():
            raw_events = [self._from_row(row) for row in raw_data]
            self.events = [EventHandle(event) for event in raw_events if event]

            self.events.sort(key=lambda handle: handle.inner.start_date)
            grouped_events = groupby(self.events, key=lambda handle: handle.inner.start_date.date())
            self.events_by_date = {key: list(items) for key, items in grouped_events}

            # We assume that main events have a duration of 3 hours
            for key, events in self.events_by_date.items():
                main_event = events[-1]
                main_event.inner = main_event.inner.copy(end_date=main_event.inner.start_date + timedelta(hours=3))

    def _from_row(self, row: dict[str, str]) -> Optional[Event]:
        # The event name and start date are required
        name = row.get('event', '').strip()
        if not name:
            return None

        start_date = self.__parse_datetime(row.get('date', '').strip(), row.get('time', '').strip())
        if not start_date:
            return None

        return Event(
            name=name,
            start_date=start_date,
            host=row.get('host', '').strip(),
            description=row.get('description', '').strip(),
        )

    def __parse_datetime(self, date_string: str, time_string: str) -> Optional[datetime]:
        try:
            full_string = date_string + ' ' + (time_string or '19:00')
            return self.timezone.localize(datetime.strptime(full_string, '%Y-%m-%d %H:%M'))
        except ValueError:
            return None
