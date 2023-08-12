from typing import List

from data.models.event import Event


class DataRepository:
    def get_events(self) -> dict[str, List[Event]]:
        pass
