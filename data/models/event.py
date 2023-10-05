from dataclasses import dataclass, replace, field
from datetime import datetime, timedelta
from copy import deepcopy


@dataclass(frozen=True)
class Event:
    name: str
    start_date: datetime
    end_date: datetime = field(default=None)
    host: str = ''
    description: str = ''

    def __post_init__(self):
        if not self.end_date:
            # Workaround to initialize a field in a frozen class
            super().__setattr__('end_date', self.start_date + timedelta(hours=1))

    def copy(self, **changes) -> 'Event':
        return replace(deepcopy(self), **changes)