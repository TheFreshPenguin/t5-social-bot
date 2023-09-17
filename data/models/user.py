from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    full_name: str
    aliases: list[str]
    telegram_username: str = ''
    birthday: str = ''
    telegram_id: Optional[int] = None
    loyverse_id: Optional[str] = None

    @property
    def first_name(self) -> str:
        return self.full_name.split(' ')[0]

    @property
    def main_alias(self) -> Optional[str]:
        return self.aliases[0] if self.aliases else None

    def __eq__(self, other):
        return self.full_name == other.full_name

    def __hash__(self):
        return hash(self.full_name)
