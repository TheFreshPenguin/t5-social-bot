import pytz

from dataclasses import dataclass, field
from datetime import datetime

from typing import Optional


@dataclass(frozen=True)
class Receipt:
    receipt_number: str
    receipt_type: str
    created_at: datetime
    receipt_date: datetime
    updated_at: datetime
    source: str
    total_money: float
    total_tax: float
    points_earned: float
    points_deducted: float
    points_balance: float
    total_discount: float
    employee_id: str
    store_id: str
    pos_device_id: str

    note: Optional[str] = None
    refund_for: Optional[str] = None
    order: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    customer_id: Optional[str] = None
    dining_option: Optional[str] = None

    tip: float = 0.0
    surcharge: float = 0.0

    total_discounts: list[dict] = field(default_factory=list)
    total_taxes: list[dict] = field(default_factory=list)

    line_items: list[dict] = field(default_factory=list)
    payments: list[dict] = field(default_factory=list)

    @staticmethod
    def from_json(data: dict, timezone: Optional[pytz.timezone] = None) -> "Receipt":
        return Receipt(**(data | {
            'created_at': Receipt._parse_datetime(data['created_at'], timezone),
            'receipt_date': Receipt._parse_datetime(data['receipt_date'], timezone),
            'updated_at': Receipt._parse_datetime(data['updated_at'], timezone),
        }))

    @staticmethod
    def _parse_datetime(date_string_utc: str, timezone: Optional[pytz.timezone]) -> datetime:
        datetime_utc = datetime.fromisoformat(date_string_utc.replace('Z', '+00:00'))
        return datetime_utc.astimezone(timezone) if timezone else datetime_utc

