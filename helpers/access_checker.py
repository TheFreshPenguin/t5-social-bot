from data.models.user import User


class AccessChecker:
    def __init__(self, masters: set, point_masters: set):
        self.masters = masters
        self.point_masters = point_masters

    def is_master(self, username: str) -> bool:
        return username in self.masters

    def can_donate_for_free(self, user: User) -> bool:
        return user.telegram_username in self.point_masters
