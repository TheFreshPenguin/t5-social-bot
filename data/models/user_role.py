from enum import Enum, unique


@unique
class UserRole(Enum):
    CHAMPION = "champion"
    STAFF = "staff"
