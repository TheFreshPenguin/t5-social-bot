from datetime import datetime, timedelta
from typing import Optional


class Event:
    def __init__(self, name: str, start_date: datetime, end_date: Optional[datetime] = None, host: str = '', description: str = ''):
        self.start_date = start_date
        # Assume a default duration of 1 hour for events
        self.end_date = end_date if end_date else (start_date + timedelta(hours=1))
        self.name = name
        self.host = host
        self.description = description
