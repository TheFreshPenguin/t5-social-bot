import requests
import json
from typing import Dict

import helpers.json
from helpers.points import Points

from integrations.loyverse.customer import Customer
from integrations.loyverse.exceptions import InsufficientFundsError


class LoyverseApi:
    BASE_URL = "https://api.loyverse.com/v1.0"
    READ_ALL_CUSTOMERS_ENDPOINT = f"{BASE_URL}/customers?updated_at_min=2023-07-01T12:30:00.000Z&limit=250"
    CREATE_OR_UPDATE_CUSTOMER_ENDPOINT = f"{BASE_URL}/customers"

    def __init__(self, token: str, read_only: bool = False):
        self.token = token
        self.read_only = read_only

    def get_balance(self, username: str) -> Points:
        return self.__get_customer(username).points

    def add_points(self, username: str, points: Points) -> None:
        customer = self.__get_customer(username)
        customer.points += points
        self.__save_customer(customer)

    def remove_points(self, username, points: Points) -> None:
        customer = self.__get_customer(username)
        if customer.points < points:
            raise InsufficientFundsError("You don't have enough points")

        customer.points -= points
        self.__save_customer(customer)

    def __get_customer(self, username: str) -> Customer:
        customers = self.__get_all_customers()
        customer = customers.get(username)

        if not customer:
            raise Exception(f"@{username} is not a recognised user, try again!")

        return customer

    def __get_all_customers(self) -> Dict[str, Customer]:
        response = requests.get(self.READ_ALL_CUSTOMERS_ENDPOINT, headers={
            "Authorization": f"Bearer {self.token}"
        })

        if response.status_code != 200:
            print(f"Loyverse get_all_customers error {response.status_code} occurred.")
            return dict()

        customers = [Customer.from_json(c) for c in response.json().get('customers')]
        return {c.username: c for c in customers if c}

    def __save_customer(self, customer: Customer) -> None:
        data = json.dumps(customer, default=helpers.json.default)
        if self.read_only:
            print(data)
            return

        response = requests.post(self.CREATE_OR_UPDATE_CUSTOMER_ENDPOINT, data=data, headers={
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        })

        if response.status_code != 200:
            print(f"Loyverse save_customer error {response.status_code} occurred.")

        print(response.json())
