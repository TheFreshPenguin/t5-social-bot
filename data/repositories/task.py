from datetime import datetime
from abc import ABC, abstractmethod

from data.models.task import Task


class TaskRepository(ABC):
    @abstractmethod
    def get_tasks_between(self, start: datetime, end: datetime) -> list[Task]:
        pass

    @abstractmethod
    def toggle(self, task: Task) -> Task:
        pass
