import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("RINGG_API_KEY")
BASE_URL = os.getenv("RINGG_BASE_URL")

def call_ringg_ai(user):
    url = f"{BASE_URL}/ca/api/v0/call"  # ⚠️ confirm endpoint

    payload = {
        "phone_number": user["phone"],
        "customer_name": user.get("name"),
        "metadata": {
            "cart_value": user.get("cart_value"),
            "source": "abandoned_checkout"
        }
    }

    headers = {
        "X-API-KEY": API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)

        if response.status_code in [200, 201]:
            return True, response.json()
        else:
            return False, response.text

    except Exception as e:
        return False, str(e)