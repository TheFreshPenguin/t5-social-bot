class AccessChecker:
    def __init__(self, masters: set, point_masters: set):
        self.masters = masters
        self.point_masters = point_masters

    def is_master(self, username: str) -> bool:
        return username in self.masters

    def can_donate_for_free(self, username: str) -> bool:
        return username in self.point_masters
