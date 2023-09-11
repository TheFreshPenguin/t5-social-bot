from datetime import date, datetime
from typing import List, Union
from abc import ABC, abstractmethod

from data.models.event import Event


class EventRepository(ABC):
    @abstractmethod
    def get_all_events(self) -> List[Event]:
        pass

    @abstractmethod
    def get_events_on(self, on_date: Union[date, datetime]) -> List[Event]:
        pass
