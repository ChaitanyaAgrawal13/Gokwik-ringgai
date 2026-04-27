import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("RINGG_API_KEY")
BASE_URL = os.getenv("RINGG_BASE_URL")

def call_ringg_ai(user, assistant_id="YOUR_ASSISTANT_ID_GOES_HERE", language="english"):
    url = f"{BASE_URL}/ca/api/v0/call"  # ⚠️ confirm endpoint

    # Grab the primary product name from the items list we saved
    items = user.get("items", [])
    product_name = items[0].get("title") if items else "your item"

    payload = {
        "phone_number": user["phone"],
        "assistant_id": assistant_id,     # <-- This tells Ringg WHICH assistant to use
        "language": language,             # <-- If Ringg supports language targeting
        "variables": {                    # <-- These map directly to {{variables}} in your Ringg AI prompt
            "customer_name": user.get("name", "there"),
            "product_name": product_name,
            "cart_value": str(user.get("cart_value")),
            "recovery_url": user.get("recovery_url", ""),
            "city": user.get("city", "your city")
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