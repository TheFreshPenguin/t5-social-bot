import requests

with open('lv_secret.txt', 'r') as file:
    LOYVERSE_TOKEN = file.read()

BASE_URL = "https://api.loyverse.com/v1.0"
READ_ALL_CUSTOMERS_ENDPOINT = f"{BASE_URL}/customers?updated_at_min=2023-07-01T12:30:00.000Z&limit=250"


def call_api(url, token):
    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, headers=headers)

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
                "lv_name": c.get("name"),
                "points": c.get("total_points")
            }

            customers[note] = infos

    return customers


# Call the API
data = call_api(READ_ALL_CUSTOMERS_ENDPOINT, LOYVERSE_TOKEN)

# Check if the API call was successful
if data is not None:
    # Process the dictionary data
    # ...
    print(data)
    print(read_customers(data))
