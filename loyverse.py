import requests
import json


class LoyverseConnector:
    BASE_URL = "https://api.loyverse.com/v1.0"
    READ_ALL_CUSTOMERS_ENDPOINT = f"{BASE_URL}/customers?updated_at_min=2023-07-01T12:30:00.000Z&limit=250"
    CREATE_OR_UPDATE_CUSTOMER_ENDPOINT = f"{BASE_URL}/customers"

    def __init__(self, token):
        self.token = token

    @staticmethod
    def is_number(variable):
        return isinstance(variable, (int, float))

    @staticmethod
    def get_customer_from_username(customers, username):
        customer = customers.get(username)
        if customer:
            return customer
        else:
            raise Exception(f"{username} is not binded with any loyverse customer")

    @staticmethod
    def read_customers(data):
        customers = {}

        for c in data.get("customers"):
            note = c.get("note")
            if note:
                infos = {
                    "note": note,
                    "id": c.get("id"),
                    "name": c.get("name"),
                    "total_points": c.get("total_points")
                }

                customers[note] = infos

        return customers

    def call_api_get(self, url):
        headers = {
            "Authorization": f"Bearer {self.token}"
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error {response.status_code} occurred.")
            return None

    def call_api_post(self, body):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        response = requests.post(self.CREATE_OR_UPDATE_CUSTOMER_ENDPOINT, headers=headers, data=json.dumps(body))

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error {response.status_code} occurred.")
            return None

    def get_all_customers(self):
        data = self.call_api_get(self.READ_ALL_CUSTOMERS_ENDPOINT)
        return self.read_customers(data)

    def get_balance(self, username):
        customers = self.get_all_customers()
        customer = self.get_customer_from_username(customers, username)
        return customer.get("total_points")

    def update_total_points(self, customer, total_points):
        customer["total_points"] = total_points
        return self.call_api_post(customer)

    def add_points(self, username, points):
        if not self.is_number(points):
            raise Exception("added points must be a number")
        if points <= 0:
            raise Exception("added points must be non-zero positive")

        customers = self.get_all_customers()

        customer = customers.get(username)
        new_total_points = customer.get("total_points") + points
        return self.update_total_points(customer, new_total_points)

    def remove_points(self, username, points):
        if not self.is_number(points):
            raise Exception("removed points must be a number")
        if points <= 0:
            raise Exception("removed points must be non-zero positive")

        customers = self.get_all_customers()

        customer = customers.get(username)
        new_total_points = customer.get("total_points") - points

        if new_total_points < 0:
            raise Exception("negative balance")

        return self.update_total_points(customer, new_total_points)

    def donate_points(self, sender_username, recipient_username, points):
        if not self.is_number(points):
            raise Exception("donated points must be a number")
        if points <= 0:
            raise Exception("donated points must be non-zero positive")

        customers = self.get_all_customers()

        recipient_customer = self.get_customer_from_username(customers, recipient_username)
        if sender_username != "roblevermusic":  # Rob can send as much points as he wants because he is god 🙏
            sender_customer = self.get_customer_from_username(customers, sender_username)
            sender_new_total_points = sender_customer.get("total_points") - points

            if sender_new_total_points < 0:
                raise Exception("you cannot donate more points than you already have")

            print(self.update_total_points(sender_customer, sender_new_total_points))

        recipient_new_total_points = recipient_customer.get("total_points") + points

        print(self.update_total_points(recipient_customer, recipient_new_total_points))
        return True


with open('lv_secret.txt', 'r') as file:
    LOYVERSE_TOKEN = file.read()

lc = LoyverseConnector(LOYVERSE_TOKEN)
try:
    # print(add_points("AntoineCastel", 100))
    print(lc.donate_points("AntoineCastel", "barbitcheps", 1))  # print True

except Exception as e:
    # Handle the exception
    print(f"Exception raised: {str(e)}")
