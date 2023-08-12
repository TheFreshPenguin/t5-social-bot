import logging
from datetime import datetime, timedelta
from typing import List
from itertools import groupby
from threading import Lock

import gspread
import pytz

from data.repository import DataRepository
from data.models.event import Event
from integrations.google.api import GoogleApi

logger = logging.getLogger(__name__)


class GoogleSheetRepository(DataRepository):
    def __init__(self, spreadsheet_key: str, api_credentials: str = None, api: GoogleApi = None, timezone: pytz.timezone = None):
        self.api = api if api else GoogleApi(api_credentials)
        self.spreadsheet_key = spreadsheet_key
        self.timezone = timezone

        # The sheet data can be read and refreshed from different threads, so any data operation needs to be protected
        self.refresh_lock = Lock()

        # The events are cached and refreshed regularly
        self.__events = {}
        self.refresh()

    def refresh(self) -> None:
        with self.refresh_lock:
            logger.info('Refreshing Google Sheets data')
            try:
                spreadsheet = self.__load_spreadsheet()
                self.__events = self.__load_events(spreadsheet)
            except Exception as e:
                logger.exception(e)

    async def refresh_job(self, context) -> None:
        self.refresh()

    def get_events(self) -> dict[str, List[Event]]:
        with self.refresh_lock:
            return self.__events

    def __load_spreadsheet(self) -> gspread.Spreadsheet:
        logger.info(f"Loading spreadsheet {self.spreadsheet_key}")
        return self.api.get_spreadsheet(self.spreadsheet_key)

    def __load_events(self, spreadsheet: gspread.Spreadsheet) -> dict[str, List[Event]]:
        try:
            raw_data = spreadsheet.worksheet('Events').get_values()
            logger.debug(f"Google Sheets Events: {raw_data}")
            return self.__parse_raw_events(raw_data)
        except Exception as e:
            logger.exception(e)
            return {}

    def __parse_raw_events(self, raw: list) -> dict[str, List[Event]]:
        if len(raw) < 2:
            raise ValueError('The event sheet does not contain the necessary data')

        header = raw[0]
        rows = raw[1:]

        keys = [h.lower().replace('(optional)', '').strip().replace(' ', '_') for h in header]
        keyed_rows = [dict(zip(keys, row)) for row in rows]

        events = [Event(
            name=row.get('event', '').strip(),
            start_date=self.__parse_datetime(row.get('date', '').strip() + ' ' + row.get('time', '').strip()),
            host=row.get('host', '').strip(),
            description=row.get('description', '').strip(),
        ) for row in keyed_rows]

        events.sort(key=lambda event: event.start_date)
        grouped_events = groupby(events, key=lambda event: event.start_date.strftime('%Y-%m-%d'))
        grouped_events = {key: list(items) for key, items in grouped_events}

        # We assume that main events have a duration of 3 hours
        for key, events in grouped_events.items():
            main_event = events[-1]
            main_event.end_date = main_event.start_date + timedelta(hours=3)

        return grouped_events

    def __parse_datetime(self, datestr: str) -> datetime:
        return self.timezone.localize(datetime.strptime(datestr, '%Y-%m-%d %H:%M'))
