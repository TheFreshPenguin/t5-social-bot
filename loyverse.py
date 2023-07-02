import requests
import json

with open('lv_secret.txt', 'r') as file:
    LOYVERSE_TOKEN = file.read()

BASE_URL = "https://api.loyverse.com/v1.0"
READ_ALL_CUSTOMERS_ENDPOINT = f"{BASE_URL}/customers?updated_at_min=2023-07-01T12:30:00.000Z&limit=250"
CREATE_OR_UPDATE_CUSTOMERS_ENDPOINT = f"{BASE_URL}/customers"


def is_number(variable):
    return isinstance(variable, (int, float))


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
                "note": note,
                "id": c.get("id"),
                "name": c.get("name"),
                "total_points": c.get("total_points")
            }

            customers[note] = infos

    return customers


def get_customers(url, token):
    data = call_api_get(READ_ALL_CUSTOMERS_ENDPOINT, LOYVERSE_TOKEN)
    return read_customers(data)


def get_balance(username):
    customers = get_customers(READ_ALL_CUSTOMERS_ENDPOINT, LOYVERSE_TOKEN)

    customer = customers.get(username)
    if customer:
        return customer.get("total_points")
    else:
        raise Exception("This username is not binded with any loyverse customer")


def update_total_points(customer, total_points):
    customer["total_points"] = total_points
    return call_api_post(CREATE_OR_UPDATE_CUSTOMERS_ENDPOINT, LOYVERSE_TOKEN, customer)


def add_points(username, points):
    if not is_number(points):
        raise Exception("added points must be a number")
    if points <= 0:
        raise Exception("added points must be non-zero positive")

    customers = get_customers(READ_ALL_CUSTOMERS_ENDPOINT, LOYVERSE_TOKEN)

    customer = customers.get(username)
    new_total_points = customer.get("total_points") + points
    return update_total_points(customer, new_total_points)


def remove_points(username, points):
    if not is_number(points):
        raise Exception("removed points must be a number")
    if points <= 0:
        raise Exception("removed points must be non-zero positive")

    customers = get_customers(READ_ALL_CUSTOMERS_ENDPOINT, LOYVERSE_TOKEN)

    customer = customers.get(username)
    new_total_points = customer.get("total_points") - points

    if new_total_points < 0:
        raise Exception("negative balance")

    return update_total_points(customer, new_total_points)


# print(get_balance("AntoineCastel"))

# data = call_api_get(READ_ALL_CUSTOMERS_ENDPOINT, LOYVERSE_TOKEN)
# customers = read_customers(data)
# print(update_total_points(customers["AntoineCastel"], 15))

try:
    print(remove_points("AntoineCastel", 10))
except Exception as e:
    # Handle the exception
    print(f"Exception raised: {str(e)}")
