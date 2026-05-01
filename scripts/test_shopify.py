import requests
import os
from dotenv import load_dotenv

load_dotenv()

SHOPIFY_TOKEN = os.getenv("SHOPIFY_API_TOKEN")
STORE_DOMAIN = "kyyhe6-ry.myshopify.com"

def test_connection():
    url = f"https://{STORE_DOMAIN}/admin/api/2023-10/orders.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
        "Content-Type": "application/json"
    }
    params = {"limit": 1}
    
    print(f"📡 Testing Shopify connection to {STORE_DOMAIN}...")
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            orders = response.json().get("orders", [])
            print(f"✅ SUCCESS! Successfully fetched {len(orders)} order(s).")
            if orders:
                print(f"📦 Latest Order Name: {orders[0].get('name')}")
        else:
            print(f"❌ FAILED: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"💥 ERROR: {e}")

if __name__ == "__main__":
    test_connection()
