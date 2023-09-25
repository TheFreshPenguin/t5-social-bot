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

    def save_users(self, key_name: str, data: dict[str, dict[str,str]]) -> None:
        self._update_sheet_data('Community', key_name, data)

    def _update_sheet_data(self, sheet_name: str, key_name: str, data: dict[str, dict[str,str]]):
        try:
            # Load the data from Google
            spreadsheet = self._load_spreadsheet()
            worksheet = self._load_worksheet(spreadsheet, sheet_name)
            raw = self._load_values(worksheet)

            header = raw[0]
            rows = raw[1:]

            # Map the header keys to their column numbers - instead of A, B, C we use 0, 1, 2
            columns = {GoogleSheetDatabase._header_to_key(h): i for i, h in enumerate(header)}

            # Index the rows by the value in the key column
            key_column = columns[key_name]
            row_number_by_key = {row[key_column]: i for i, row in enumerate(rows)}

            for key, update in data.items():
                row_number = row_number_by_key.get(key, None)
                if row_number is None:
                    continue

                # Map the updates to their column numbers
                updates_by_column = {columns[k]: v for k, v in update.items() if k in columns}
                # We add 1 to the row to account for the headers
                GoogleSheetDatabase._update_row(worksheet, row_number + 1, updates_by_column)
        except Exception as e:
            logger.exception(e)

    @staticmethod
    def _update_row(worksheet: gspread.Worksheet, row_number: int, updates_by_column: dict[int, str]) -> None:
        for k, v in updates_by_column.items():
            worksheet.update_cell(row_number + 1, k + 1, v)  # Coordinates start at 1


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
            op.map(lambda worksheet: GoogleSheetDatabase._load_values(worksheet)),  # Load the actual data
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
    def _load_worksheet(spreadsheet: gspread.Spreadsheet, sheet_name: str) -> gspread.Worksheet:
        logger.debug(f"Loading worksheet {sheet_name}")
        return spreadsheet.worksheet(sheet_name)

    @staticmethod
    def _load_values(worksheet: gspread.Worksheet) -> list[list]:
        logger.debug(f"Loading worksheet values")
        return worksheet.get_values()

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
