import pytz

from typing import Optional
from datetime import datetime, time

from readerwriterlock import rwlock

from data.repositories.task import TaskRepository
from data.models.task import Task

from integrations.google.handle import Handle
from integrations.google.sheet_database import GoogleSheetDatabase

TaskHandle = Handle[Task]


class GoogleSheetTaskRepository(TaskRepository):
    def __init__(self, database: GoogleSheetDatabase, timezone: pytz.timezone = None):
        self.timezone = timezone

        self.tasks: list[TaskHandle] = []

        # The repository data can be read and refreshed from different threads,
        # so any data operation needs to be protected
        self.lock = rwlock.RWLockWrite()

        self.database = database
        database.tasks.subscribe(self._load)

    def get_tasks_between(self, start: datetime, end: datetime) -> list[Task]:
        weekday = start.weekday()
        start_time = start.time()
        end_time = end.time()
        tasks = [task.inner for task in self.tasks if task.inner.weekday == weekday and start_time <= task.inner.time < end_time]
        return tasks

    def toggle(self, task: Task) -> Task:
        new_task = task.copy(is_done=not task.is_done)

        with self.lock.gen_wlock():
            # Only existing tasks can be toggled
            existing = next((handle for handle in self.tasks if handle.inner == task), None)
            if existing:
                existing.inner = new_task

            self.database.check_task(self._to_row(new_task))

        return new_task

    def _load(self, raw_data: list[dict[str, str]]) -> None:
        with self.lock.gen_wlock():
            last_times = [self._parse_time('08:00') for i in range(0, 7)]
            self.tasks = []
            for row in raw_data:
                task = self._from_row(row, last_times)
                if task:
                    last_times[task.weekday] = task.time
                    self.tasks.append(TaskHandle(task))

    def _from_row(self, row: dict[str, str], last_times: list[time]) -> Optional[Task]:
        # If the name is not provided, this indicates an empty row
        name = row.get('name', '').strip()
        if not name:
            return None

        weekday = int(row['weekday'])
        return Task(
            weekday=weekday,
            time=GoogleSheetTaskRepository._parse_time(row.get('time', '').strip()) or last_times[weekday],
            name=name,
            is_done=row['is_done'] != ''
        )

    @staticmethod
    def _to_row(task: Task) -> dict[str, str]:
        return {
            'weekday': str(task.weekday),
            'time': task.time.strftime('%H:%M'),
            'name': task.name,
            'is_done': 'x' if task.is_done else ''
        }

    @staticmethod
    def _parse_time(time_string: str) -> Optional[time]:
        try:
            return time.fromisoformat(time_string)
        except ValueError:
            return None
