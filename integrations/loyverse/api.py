import logging
import requests
import json
import pytz
from typing import Optional, Generator
from datetime import datetime

import helpers.json
from helpers.points import Points

from data.models.user import User
from data.repositories.user import UserRepository

from integrations.loyverse.customer import Customer
from integrations.loyverse.receipt import Receipt
from integrations.loyverse.exceptions import InsufficientFundsError, InvalidCustomerError

logger = logging.getLogger(__name__)


class LoyverseApi:
    BASE_URL = "https://api.loyverse.com/v1.0"
    CUSTOMERS_ENDPOINT = f"{BASE_URL}/customers"
    READ_ALL_CUSTOMERS_ENDPOINT = f"{CUSTOMERS_ENDPOINT}?updated_at_min=2023-07-01T12:30:00.000Z&limit=250"
    RECEIPTS_ENDPOINT = f"{BASE_URL}/receipts"

    def __init__(self, token: str, users: UserRepository, read_only: bool = False):
        self.token = token
        self.users = users
        self.read_only = read_only

    def get_balance(self, user: User) -> Points:
        return self._get_customer(user).points

    def add_points(self, user: User, points: Points) -> None:
        if points.is_zero:
            return

        customer = self._get_customer(user)
        customer.points += points
        self._save_customer(customer)

    def remove_points(self, user: User, points: Points) -> None:
        if points.is_zero:
            return

        customer = self._get_customer(user)
        if customer.points < points:
            raise InsufficientFundsError("You don't have enough points")

        customer.points -= points
        self._save_customer(customer)

    def get_receipts(self, since: datetime) -> Generator[Receipt, None, None]:
        since_utc = since.replace(microsecond=0).astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
        limit = 50
        cursor = None

        # Emulate do-while
        while True:
            response = requests.get(
                f"{self.RECEIPTS_ENDPOINT}",
                params={'created_at_min': since_utc, 'limit': limit, 'cursor': cursor},
                headers={"Authorization": f"Bearer {self.token}"}
            )

            if response.status_code != 200:
                logger.error(f"Loyverse get_receipts error {response.status_code} occurred.")
                break

            response_data = response.json()
            raw_receipts = response_data.get('receipts', [])
            cursor = response_data.get('cursor')

            for raw_receipt in raw_receipts:
                yield Receipt.from_json(raw_receipt, since.tzinfo)

            if not cursor or len(raw_receipts) < limit:
                break


    def _get_customer(self, user: User) -> Customer:
        customer = self._get_single_customer(user.loyverse_id) if user.loyverse_id else None

        if not customer:
            customer = self._initialize_customer(user)

        if not customer:
            raise InvalidCustomerError(f"The user @{user.telegram_username} is not a recognized Loyverse customer.")

        return customer

    def _get_single_customer(self, customer_id: str) -> Optional[Customer]:
        response = requests.get(f"{self.CUSTOMERS_ENDPOINT}/{customer_id}", headers={
            "Authorization": f"Bearer {self.token}"
        })

        if response.status_code != 200:
            logger.error(f"Loyverse get_single_customer error {response.status_code} occurred.")
            return None

        return Customer.from_json(response.json())

    def _initialize_customer(self, user: User) -> Optional[Customer]:
        if not user.telegram_username:
            return None

        customers = self._get_all_customers()
        customer = customers.get(user.telegram_username)
        if not customer:
            return None

        # Save the customer id to the user data for future reference
        user = user.copy(loyverse_id=customer.customer_id)
        self.users.save(user)

        return customer

    def _get_all_customers(self) -> dict[str, Customer]:
        response = requests.get(self.READ_ALL_CUSTOMERS_ENDPOINT, headers={
            "Authorization": f"Bearer {self.token}"
        })

        if response.status_code != 200:
            logger.error(f"Loyverse get_all_customers error {response.status_code} occurred.")
            return dict()

        customers = [Customer.from_json(c) for c in response.json().get('customers')]
        return {c.username: c for c in customers if c}

    def _save_customer(self, customer: Customer) -> None:
        data = json.dumps(customer, default=helpers.json.default)
        if self.read_only:
            logger.info(data)
            return

        response = requests.post(self.CUSTOMERS_ENDPOINT, data=data, headers={
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        })

        if response.status_code != 200:
            logger.error(f"Loyverse save_customer error {response.status_code} occurred.")

        logger.info(response.json())

