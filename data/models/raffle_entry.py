from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RaffleEntry:
    full_name: str
    created_at: datetime
    country: str
