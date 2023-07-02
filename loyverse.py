import requests
import json

with open('lv_secret.txt', 'r') as file:
    LOYVERSE_TOKEN = file.read()

BASE_URL = "https://api.loyverse.com/v1.0"
READ_ALL_CUSTOMERS_ENDPOINT = f"{BASE_URL}/customers?updated_at_min=2023-07-01T12:30:00.000Z&limit=250"
CREATE_OR_UPDATE_CUSTOMERS_ENDPOINT = f"{BASE_URL}/customers"


def call_api_get(url, token):
    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error {response.status_code} occurred.")
        return None


def call_api_post(url, token, body):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, data=json.dumps(body))

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error {response.status_code} occurred.")
        return None


def read_customers(data):
    customers = {}

    for c in data.get("customers"):
        note = c.get("note")
        if note:
            infos = {
                "id": c.get("id"),
                "name": c.get("name"),
                "total_points": c.get("total_points")
            }

            customers[note] = infos

    return customers


def get_balance(username):
    data = call_api_get(READ_ALL_CUSTOMERS_ENDPOINT, LOYVERSE_TOKEN)
    customers = read_customers(data)

    customer = customers.get(username)
    if customer:
        return customer.get("total_points")
    else:
        return None


# def update_points(username, points):
#
#     body =
#     call_api_post(CREATE_OR_UPDATE_CUSTOMERS_ENDPOINT, LOYVERSE_TOKEN, customer)


# def add_points(username):


print(get_balance("AntoineCastel"))
