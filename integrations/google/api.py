import json
import gspread


class GoogleApi:
    def __init__(self, credentials: str):
        try:
            self.credentials = json.loads(credentials)
        except TypeError as e:
            raise TypeError('Could not parse the Google API credentials') from e

    def get_spreadsheet(self, key: str) -> gspread.Spreadsheet:
        try:
            gc = gspread.service_account_from_dict(self.credentials)
            return gc.open_by_key(key)
        except Exception as e:
            raise Exception(f'Could not open the spreadsheet {key}') from e
