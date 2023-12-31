import logging
from datetime import datetime, date, timedelta
from itertools import groupby
from typing import Optional, Tuple

from data.models.user import User

from modules.base_module import BaseModule
from helpers.points import Points

logger = logging.getLogger(__name__)

Checkpoints = dict[int, Points]
ReachedCheckpoints = dict[date, Checkpoints]


class VisitCalculator(BaseModule):
    def __init__(self, checkpoints: Checkpoints):
        # Make sure the checkpoints are sorted
        self._checkpoints = dict(sorted(checkpoints.items()))

    @staticmethod
    def get_visits_this_month(user: User, current_month: datetime) -> int:
        if user.last_visit and VisitCalculator.month(user.last_visit) >= VisitCalculator.month(current_month):
            return user.recent_visits

        return 0

    def get_next_checkpoint(self, visits: int) -> Optional[Tuple[int, Points]]:
        for checkpoint, points in self._checkpoints.items():
            if checkpoint > visits:
                return checkpoint, points
        return None

    def add_visits(self, raw_visits: list[Tuple[User, datetime]], current_month: datetime) -> dict[User, ReachedCheckpoints]:
        if not raw_visits:
            return {}

        current_month = VisitCalculator.month(current_month)

        # Group the visits by User
        sorted_visits = sorted(raw_visits, key=lambda visit: visit[0].full_name)
        grouped_visits = groupby(sorted_visits, key=lambda visit: visit[0])
        user_visits = {user: [visit[1] for visit in visits] for user, visits in grouped_visits}

        # Add the visits to each user
        raw_updates = [self._add_user_visits(user, visits, current_month) for user, visits in user_visits.items()]
        updates = {update[0]: update[1] for update in raw_updates if update}
        return updates

    def _add_user_visits(self, user: User, raw_visits: list[datetime], current_month: date) -> Optional[Tuple[User, ReachedCheckpoints]]:
        clean_visits = VisitCalculator._clean_visits(raw_visits, user.last_visit)
        if not clean_visits:
            return None

        # Grouping the visits by month helps us deal with various edge cases
        # 1. We have crossed from one month into another and we need to start the count again from 0 (most common)
        # 2. The visits span more than 1 month (extremely rare edge case)
        #    E.g. This is possible if we last checked on November 30th at 12:00 and it's now December 1st at 12:00
        #    Some visits could have come in during this 24 hour interval and they would be in different months
        # 3. The bot has been shut down for a while and we are dealing with an incoming flux of historical data
        #    spanning many months, and we need to grant partial points for one month and full points for the rest
        visits_by_month = {}
        if user.last_visit:
            visits_by_month[VisitCalculator.month(user.last_visit)] = user.recent_visits

        month_checkpoints = {}
        for month, visits in VisitCalculator._count_visits_by_month(clean_visits).items():
            old_count = visits_by_month.get(month, 0)
            new_count = old_count + visits
            visits_by_month[month] = new_count
            checkpoints = self._reach_checkpoints(old_count, new_count)
            if checkpoints:
                month_checkpoints[month] = checkpoints

        updated_user = user.copy(
            recent_visits=visits_by_month.get(current_month, 0),
            last_visit=clean_visits[-1],
        )

        return updated_user, month_checkpoints

    @staticmethod
    def _clean_visits(visits: list[datetime], last_visit: Optional[datetime]) -> list[datetime]:
        # Clean up the list of raw visits by:
        # - Removing old visits
        # - Sorting them by date
        # - Removing duplicate visits

        # Keep only visits that are newer than the user's last visit
        new_visits = [visit for visit in visits if visit > last_visit] if last_visit else visits
        if not new_visits:
            return []

        new_visits = sorted(new_visits)

        # Keep only visits that happen more than 8 hours after each other
        distance = timedelta(hours=8)

        distinct_visits = []
        next_allowed_visit = last_visit + distance if last_visit else new_visits[0]
        for visit in new_visits:
            if visit >= next_allowed_visit:
                distinct_visits.append(visit)
                next_allowed_visit = visit + distance

        return distinct_visits

    @staticmethod
    def _count_visits_by_month(visits: list[datetime]) -> dict[date, int]:
        # Group by month and count the visits
        visits_grouped_by_month = groupby(sorted(visits), key=lambda visit: VisitCalculator.month(visit))
        return {month: len(list(visits)) for month, visits in visits_grouped_by_month}

    def _reach_checkpoints(self, start: int, end: int) -> Checkpoints:
        return {visits: points for visits, points in self._checkpoints.items() if start < visits <= end}

    @staticmethod
    def month(value: datetime) -> date:
        return value.date().replace(day=1)
