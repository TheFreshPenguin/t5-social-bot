import logging
import re
from reactivex import Observable, operators as op
from reactivex.subject import BehaviorSubject, Subject

import gspread

from integrations.google.api import GoogleApi

logger = logging.getLogger(__name__)


class GoogleSheetDatabase:
    def __init__(self, spreadsheet_key: str, api_credentials: str = None, api: GoogleApi = None):
        self.api = api if api else GoogleApi(api_credentials)
        self.spreadsheet_key = spreadsheet_key

        self._spreadsheet = Subject()
        self._events = self._sheet_data('Events')
        self._users = self._sheet_data('Community')

        self.refresh()

    @property
    def events(self) -> Observable:
        return self._events

    @property
    def users(self) -> Observable:
        return self._users

    def refresh(self) -> None:
        logger.info('Refreshing Google Sheets data')
        try:
            self._spreadsheet.on_next(self._load_spreadsheet())
        except Exception as e:
            self._spreadsheet.on_error(e)

    async def refresh_job(self, context) -> None:
        self.refresh()

    def _sheet_data(self, sheet: str) -> Observable:
        cached_data = BehaviorSubject([])  # Start with an empty array until we get some data

        self._spreadsheet.pipe(  # Start with the spreadsheet
            op.map(lambda spreadsheet: GoogleSheetDatabase._load_worksheet(spreadsheet, sheet)),  # Load the sheet
            op.distinct_until_changed(),  # Only propagate when the sheet data changes, because it rarely changes
            op.map(lambda data: GoogleSheetDatabase._parse_sheet_data(data)),  # Parse the data
        ).subscribe(
            on_next=lambda data: cached_data.on_next(data),   # Propagate the parsed data to the cache
            on_error=lambda e: logger.exception(e),  # Log errors
        )

        return cached_data

    def _load_spreadsheet(self) -> gspread.Spreadsheet:
        logger.info(f"Loading spreadsheet {self.spreadsheet_key}")
        return self.api.get_spreadsheet(self.spreadsheet_key)

    @staticmethod
    def _load_worksheet(spreadsheet: gspread.Spreadsheet, worksheet: str) -> list[list]:
        logger.debug(f"Loading worksheet {worksheet}")
        return spreadsheet.worksheet(worksheet).get_values()

    @staticmethod
    def _parse_sheet_data(raw: list[list]) -> list[dict]:
        if len(raw) < 2:
            raise ValueError("The sheet does not contain the necessary data")

        header = raw[0]
        rows = raw[1:]

        keys = [GoogleSheetDatabase._header_to_key(h) for h in header]
        return [dict(zip(keys, row)) for row in rows]

    @staticmethod
    def _header_to_key(text: str) -> str:
        return (
            re.sub(r"\([^)]*\)", '', text)  # Remove anything in parentheses
            .lower()
            .strip()
            .replace(' ', '_')
        )
